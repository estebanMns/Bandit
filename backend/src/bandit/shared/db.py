"""Infraestructura de base de datos compartida por los módulos."""

from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Dialect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    """Base declarativa común. Cada módulo define sus propias tablas."""


class UtcDateTime(TypeDecorator[datetime]):
    """Fecha con zona horaria también en SQLite, que no la conserva."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: Any, dialect: Dialect) -> datetime | None:
        if not isinstance(value, datetime):
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value


# Supabase cierra conexiones inactivas: se renuevan antes de que eso pase.
_POOL_RECYCLE_SECONDS = 240


def create_engine(url: str) -> AsyncEngine:
    # Sin pre_ping: con la base lejos, cada ping cuesta un viaje completo por consulta.
    return create_async_engine(url, pool_recycle=_POOL_RECYCLE_SECONDS)


class SessionFactory:
    """Lecturas sin transacción y escrituras con transacción, sobre el mismo pool.

    Una lectura en autocommit se resuelve en un solo viaje, sin BEGIN ni ROLLBACK.
    Toda escritura debe usar `begin()`, que mantiene la atomicidad.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        readonly = engine.execution_options(isolation_level="AUTOCOMMIT")
        self._read = async_sessionmaker(readonly, expire_on_commit=False)
        self._write = async_sessionmaker(engine, expire_on_commit=False)

    def __call__(self) -> AsyncSession:
        return self._read()

    def begin(self) -> AbstractAsyncContextManager[AsyncSession]:
        return self._write.begin()


def create_session_factory(engine: AsyncEngine) -> SessionFactory:
    return SessionFactory(engine)
