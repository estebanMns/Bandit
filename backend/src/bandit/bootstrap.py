"""Raíz de composición: el único lugar que conoce las implementaciones concretas."""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncEngine

from bandit.cameras.infrastructure import tables as camera_tables  # noqa: F401
from bandit.cameras.infrastructure.fernet_cipher import FernetUrlCipher
from bandit.cameras.infrastructure.ffmpeg_source import FfmpegFrameSource
from bandit.cameras.module import CamerasModule
from bandit.establishments.infrastructure import tables as establishment_tables  # noqa: F401
from bandit.establishments.module import EstablishmentsModule
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
    establishments: EstablishmentsModule
    cameras: CamerasModule


def build_application(settings: Settings) -> Application:
    engine = create_engine(settings.database_url)
    sessions = create_session_factory(engine)
    clock = SystemClock()
    bus = InMemoryEventBus()

    identity = IdentityModule(
        sessions,
        clock,
        timedelta(hours=settings.session_ttl_hours),
        settings.cookie_secure,
    )
    establishments = EstablishmentsModule(sessions)
    cameras = CamerasModule(
        sessions,
        FfmpegFrameSource(settings.ffmpeg_path, settings.video_fps, settings.video_width),
        FernetUrlCipher(settings.camera_encryption_key),
        bus,
        clock,
    )
    return Application(
        engine=engine, identity=identity, establishments=establishments, cameras=cameras
    )
