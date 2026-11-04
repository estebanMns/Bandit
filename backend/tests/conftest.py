"""Accesorios comunes: base de datos en memoria y reloj controlable."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

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
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    import bandit.bootstrap  # noqa: F401  Registra todas las tablas.

    # Archivo y conexiones separadas: las transacciones concurrentes son reales.
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        poolclass=NullPool,
        connect_args={"timeout": 5},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def sessions(engine: AsyncEngine) -> SessionFactory:
    return create_session_factory(engine)
