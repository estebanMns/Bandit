"""Repositorios SQL de identidad."""

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from bandit.identity.domain.models import Role, Session, User
from bandit.identity.infrastructure.tables import SessionRow, UserRow
from bandit.shared.db import SessionFactory
from bandit.shared.errors import ConflictError


def _to_user(row: UserRow) -> User:
    return User(
        id=row.id,
        email=row.email,
        password_hash=row.password_hash,
        role=Role(row.role),
        establishment_id=row.establishment_id,
    )


class SqlUserRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def add(self, user: User) -> None:
        try:
            async with self._sessions.begin() as session:
                session.add(
                    UserRow(
                        id=user.id,
                        email=user.email,
                        password_hash=user.password_hash,
                        role=user.role.value,
                        establishment_id=user.establishment_id,
                    )
                )
        except IntegrityError as error:
            # Dos registros simultáneos con el mismo correo: la base de datos decide.
            raise ConflictError("Ya existe un usuario con ese correo") from error

    async def get(self, user_id: UUID) -> User | None:
        async with self._sessions() as session:
            row = await session.get(UserRow, user_id)
            return _to_user(row) if row else None

    async def get_by_email(self, email: str) -> User | None:
        async with self._sessions() as session:
            row = await session.scalar(select(UserRow).where(UserRow.email == email))
            return _to_user(row) if row else None

    async def count(self) -> int:
        async with self._sessions() as session:
            return await session.scalar(select(func.count()).select_from(UserRow)) or 0

    async def set_password(self, user_id: UUID, password_hash: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(
                update(UserRow).where(UserRow.id == user_id).values(password_hash=password_hash)
            )

    async def delete(self, user_id: UUID) -> None:
        async with self._sessions.begin() as session:
            await session.execute(delete(SessionRow).where(SessionRow.user_id == user_id))
            await session.execute(delete(UserRow).where(UserRow.id == user_id))


class SqlSessionRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def add(self, session_model: Session) -> None:
        async with self._sessions.begin() as session:
            session.add(
                SessionRow(
                    token_hash=session_model.token_hash,
                    user_id=session_model.user_id,
                    expires_at=session_model.expires_at,
                )
            )

    async def get(self, token_hash: str) -> Session | None:
        async with self._sessions() as session:
            row = await session.get(SessionRow, token_hash)
            return Session(row.token_hash, row.user_id, row.expires_at) if row else None

    async def delete(self, token_hash: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(delete(SessionRow).where(SessionRow.token_hash == token_hash))

    async def get_with_user(self, token_hash: str) -> tuple[Session, User] | None:
        async with self._sessions() as session:
            found = (
                await session.execute(
                    select(SessionRow, UserRow)
                    .join(UserRow, UserRow.id == SessionRow.user_id)
                    .where(SessionRow.token_hash == token_hash)
                )
            ).first()
            if found is None:
                return None
            row, user = found
            return Session(row.token_hash, row.user_id, row.expires_at), _to_user(user)
