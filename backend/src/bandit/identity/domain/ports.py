"""Puertos que el módulo de identidad necesita del exterior."""

from typing import Protocol
from uuid import UUID

from bandit.identity.domain.models import Session, User


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def count(self) -> int: ...

    async def set_password(self, user_id: UUID, password_hash: str) -> None: ...

    async def delete(self, user_id: UUID) -> None:
        """Borra el usuario y sus sesiones."""
        ...


class SessionRepository(Protocol):
    async def add(self, session: Session) -> None: ...

    async def get(self, token_hash: str) -> Session | None: ...

    async def delete(self, token_hash: str) -> None: ...


class EstablishmentCreator(Protocol):
    """Crea el local de una cuenta nueva sin que identidad conozca ese módulo."""

    async def create(self, name: str, address: str) -> UUID: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...
