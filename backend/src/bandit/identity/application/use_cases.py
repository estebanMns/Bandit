"""Casos de uso de identidad."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from bandit.identity.application.throttle import LoginThrottle
from bandit.identity.domain.models import Role, Session, User
from bandit.identity.domain.ports import PasswordHasher, SessionRepository, UserRepository
from bandit.shared.clock import Clock
from bandit.shared.errors import AuthenticationError, ConflictError, InvalidDataError

MIN_PASSWORD_LENGTH = 12


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@dataclass(frozen=True, slots=True)
class IssuedSession:
    token: str
    user: User


class RegisterUser:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    async def execute(
        self, email: str, password: str, role: Role, establishment_id: UUID | None = None
    ) -> User:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidDataError(f"La clave debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")
        normalized = _normalize_email(email)
        if await self._users.get_by_email(normalized):
            raise ConflictError("Ya existe un usuario con ese correo")
        user = User(
            id=uuid4(),
            email=normalized,
            password_hash=self._hasher.hash(password),
            role=role,
            establishment_id=establishment_id,
        )
        await self._users.add(user)
        return user


class BootstrapAdmin:
    """Crea el primer administrador si la base de datos no tiene usuarios."""

    def __init__(self, users: UserRepository, register: RegisterUser) -> None:
        self._users = users
        self._register = register

    async def execute(self, email: str, password: str) -> None:
        if email and password and await self._users.count() == 0:
            await self._register.execute(email, password, Role.ADMIN)


class Login:
    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        hasher: PasswordHasher,
        clock: Clock,
        ttl: timedelta,
        throttle: LoginThrottle,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._hasher = hasher
        self._clock = clock
        self._ttl = ttl
        self._throttle = throttle
        self._decoy_hash = hasher.hash(secrets.token_urlsafe(32))

    async def execute(self, email: str, password: str) -> IssuedSession:
        normalized = _normalize_email(email)
        now = self._clock.now()
        if self._throttle.is_blocked(normalized, now):
            raise AuthenticationError("Demasiados intentos. Espera unos minutos.")

        user = await self._users.get_by_email(normalized)
        # Se verifica siempre para no revelar por tiempo si el correo existe.
        stored_hash = user.password_hash if user else self._decoy_hash
        verified = self._hasher.verify(stored_hash, password)
        if user is None or not verified:
            self._throttle.record_failure(normalized, now)
            raise AuthenticationError("Correo o clave incorrectos")

        self._throttle.reset(normalized)
        token = secrets.token_urlsafe(32)
        await self._sessions.add(Session(_hash_token(token), user.id, now + self._ttl))
        return IssuedSession(token=token, user=user)


class Logout:
    def __init__(self, sessions: SessionRepository) -> None:
        self._sessions = sessions

    async def execute(self, token: str) -> None:
        await self._sessions.delete(_hash_token(token))


class AuthenticateSession:
    def __init__(self, users: UserRepository, sessions: SessionRepository, clock: Clock) -> None:
        self._users = users
        self._sessions = sessions
        self._clock = clock

    async def execute(self, token: str) -> User:
        token_hash = _hash_token(token)
        session = await self._sessions.get(token_hash)
        if session is None:
            raise AuthenticationError("Sesión no válida")
        if session.is_expired(self._clock.now()):
            await self._sessions.delete(token_hash)
            raise AuthenticationError("La sesión expiró")
        user = await self._users.get(session.user_id)
        if user is None:
            raise AuthenticationError("Sesión no válida")
        return user
