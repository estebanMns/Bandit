"""Raíz de composición: el único lugar que conoce las implementaciones concretas."""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncEngine

from bandit.identity.infrastructure import tables as identity_tables  # noqa: F401
from bandit.identity.module import IdentityModule
from bandit.shared.clock import SystemClock
from bandit.shared.config import Settings
from bandit.shared.db import create_engine, create_session_factory
from bandit.shared.events import InMemoryEventBus


@dataclass(slots=True)
class Application:
    engine: AsyncEngine
    identity: IdentityModule


def build_application(settings: Settings) -> Application:
    engine = create_engine(settings.database_url)
    sessions = create_session_factory(engine)
    clock = SystemClock()
    InMemoryEventBus()

    identity = IdentityModule(
        sessions,
        clock,
        timedelta(hours=settings.session_ttl_hours),
        settings.cookie_secure,
    )
    return Application(engine=engine, identity=identity)
