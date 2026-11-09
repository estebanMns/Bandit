"""Casos de uso de identidad."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from bandit.identity.application.session_cache import SessionCache
from bandit.identity.application.throttle import AttemptThrottle
from bandit.identity.domain.models import Role, Session, User
from bandit.identity.domain.ports import (
    EstablishmentCreator,
    PasswordHasher,
    SessionRepository,
    UserRepository,
)
from bandit.shared.clock import Clock
from bandit.shared.errors import (
    AuthenticationError,
    ConflictError,
    InvalidDataError,
    RateLimitedError,
)

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

    async def validate(self, email: str, password: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidDataError(f"La clave debe tener al menos {MIN_PASSWORD_LENGTH} caracteres")
        if await self._users.get_by_email(_normalize_email(email)):
            raise ConflictError("Ya existe un usuario con ese correo")

    async def execute(
        self, email: str, password: str, role: Role, establishment_id: UUID | None = None
    ) -> User:
        await self.validate(email, password)
        normalized = _normalize_email(email)
        user = User(
            id=uuid4(),
            email=normalized,
            password_hash=self._hasher.hash(password),
            role=role,
            establishment_id=establishment_id,
        )
        await self._users.add(user)
        return user


class SignUp:
    """Registro abierto: crea un local y su dueño. Nunca concede el rol de administrador."""

    def __init__(
        self,
        register: RegisterUser,
        establishments: EstablishmentCreator,
        throttle: AttemptThrottle,
        clock: Clock,
    ) -> None:
        self._register = register
        self._establishments = establishments
        self._throttle = throttle
        self._clock = clock

    async def execute(
        self, email: str, password: str, local_name: str, local_address: str, client_key: str
    ) -> User:
        now = self._clock.now()
        if self._throttle.is_blocked(client_key, now):
            raise RateLimitedError("Demasiados registros desde esta conexión. Espera un momento.")
        await self._register.validate(email, password)
        self._throttle.record(client_key, now)
        establishment_id = await self._establishments.create(local_name, local_address)
        return await self._register.execute(email, password, Role.OWNER, establishment_id)


class BootstrapAdmin:
    """Crea el primer administrador si la base de datos no tiene usuarios."""

    def __init__(self, users: UserRepository, register: RegisterUser) -> None:
        self._users = users
        self._register = register

    async def execute(self, email: str, password: str) -> None:
        if email and password and await self._users.count() == 0:
            await self._register.execute(email, password, Role.ADMIN)


DEMO_USERNAME = "admin"
DEMO_PASSWORD = "admin"  # noqa: S105  Clave de prueba a propósito; solo con DEMO_ADMIN=true.


class SyncDemoAdmin:
    """Cuenta admin/admin solo para pruebas. Con el modo apagado, la cuenta deja de existir.

    El registro exige un correo válido, así que "admin" nunca puede ser una cuenta real.
    """

    def __init__(self, users: UserRepository, hasher: PasswordHasher, cache: SessionCache) -> None:
        self._users = users
        self._hasher = hasher
        self._cache = cache

    async def execute(self, enabled: bool) -> None:
        existing = await self._users.get_by_email(DEMO_USERNAME)
        if not enabled:
            if existing is not None:
                self._cache.forget_user(existing.id)
                await self._users.delete(existing.id)
            return
        password_hash = self._hasher.hash(DEMO_PASSWORD)
        if existing is None:
            await self._users.add(
                User(
                    id=uuid4(),
                    email=DEMO_USERNAME,
                    password_hash=password_hash,
                    role=Role.ADMIN,
                    establishment_id=None,
                )
            )
        elif existing.role is not Role.ADMIN:
            # Con ese nombre solo puede existir la cuenta de prueba: se rehace como admin.
            self._cache.forget_user(existing.id)
            await self._users.delete(existing.id)
            await self.execute(enabled)
        elif not self._hasher.verify(existing.password_hash, DEMO_PASSWORD):
            await self._users.set_password(existing.id, password_hash)


class Login:
    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        hasher: PasswordHasher,
        clock: Clock,
        ttl: timedelta,
        throttle: AttemptThrottle,
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
            self._throttle.record(normalized, now)
            raise AuthenticationError("Correo o clave incorrectos")

        self._throttle.reset(normalized)
        token = secrets.token_urlsafe(32)
        await self._sessions.add(Session(_hash_token(token), user.id, now + self._ttl))
        return IssuedSession(token=token, user=user)


class Logout:
    def __init__(self, sessions: SessionRepository, cache: SessionCache) -> None:
        self._sessions = sessions
        self._cache = cache

    async def execute(self, token: str) -> None:
        token_hash = _hash_token(token)
        self._cache.forget(token_hash)
        await self._sessions.delete(token_hash)


class AuthenticateSession:
    def __init__(self, sessions: SessionRepository, clock: Clock, cache: SessionCache) -> None:
        self._sessions = sessions
        self._clock = clock
        self._cache = cache

    async def execute(self, token: str) -> User:
        token_hash = _hash_token(token)
        now = self._clock.now()
        cached = self._cache.get(token_hash, now)
        if cached is not None:
            return cached
        found = await self._sessions.get_with_user(token_hash)
        if found is None:
            raise AuthenticationError("Sesión no válida")
        session, user = found
        if session.is_expired(now):
            await self._sessions.delete(token_hash)
            raise AuthenticationError("La sesión expiró")
        self._cache.put(token_hash, user, session.expires_at, now)
        return user
