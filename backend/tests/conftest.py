"""Accesorios comunes: base de datos en memoria y reloj controlable."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from bandit.shared.db import Base, SessionFactory, create_session_factory


@dataclass
class FakeClock:
    current: datetime = field(default_factory=lambda: datetime(2026, 11, 4, 22, 0, tzinfo=UTC))

    def now(self) -> datetime:
        return self.current

    def advance(self, **kwargs: float) -> None:
        self.current += timedelta(**kwargs)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    import bandit.bootstrap  # noqa: F401  Registra todas las tablas.

    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def sessions(engine: AsyncEngine) -> SessionFactory:
    return create_session_factory(engine)
