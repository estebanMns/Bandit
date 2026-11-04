"""Raíz de composición: el único lugar que conoce las implementaciones concretas."""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from bandit.analysis.domain.models import SituationDetected
from bandit.analysis.domain.ports import SceneAnalyzer
from bandit.analysis.infrastructure.gemini_analyzer import (
    DisabledSceneAnalyzer,
    GeminiSceneAnalyzer,
)
from bandit.analysis.module import AnalysisModule
from bandit.cameras.domain.models import CameraStatusChanged
from bandit.cameras.infrastructure import tables as camera_tables  # noqa: F401
from bandit.cameras.infrastructure.fernet_cipher import FernetUrlCipher
from bandit.cameras.infrastructure.ffmpeg_source import FfmpegFrameSource
from bandit.cameras.module import CamerasModule
from bandit.directory.domain.ports import DirectoryAgent
from bandit.directory.infrastructure import tables as directory_tables  # noqa: F401
from bandit.directory.infrastructure.file_media import FileMediaStore
from bandit.directory.infrastructure.gemini_agent import (
    DisabledDirectoryAgent,
    GeminiDirectoryAgent,
)
from bandit.directory.infrastructure.next_revalidator import NextRevalidator
from bandit.directory.infrastructure.polite_fetcher import PoliteFetcher
from bandit.directory.module import DirectoryModule
from bandit.establishments.infrastructure import tables as establishment_tables  # noqa: F401
from bandit.establishments.module import EstablishmentsModule
from bandit.identity.infrastructure import tables as identity_tables  # noqa: F401
from bandit.identity.module import IdentityModule
from bandit.incidents.domain.models import IncidentChanged, IncidentConfirmed
from bandit.incidents.infrastructure import tables as incident_tables  # noqa: F401
from bandit.incidents.infrastructure.file_evidence import FileEvidenceStore
from bandit.incidents.module import IncidentsModule
from bandit.notifications.domain.models import AlertDelivered, AlertFailed
from bandit.notifications.infrastructure import tables as notification_tables  # noqa: F401
from bandit.notifications.infrastructure.web_push import VapidPushSender
from bandit.notifications.infrastructure.whatsapp_cloud import WhatsAppCloudSender
from bandit.notifications.module import NotificationsModule
from bandit.realtime.application.event_hub import EventHub
from bandit.realtime.application.translators import LiveEventPublisher
from bandit.shared.clock import SystemClock
from bandit.shared.config import Settings
from bandit.shared.db import create_engine, create_session_factory
from bandit.shared.events import EventBus, InMemoryEventBus


@dataclass(slots=True)
class Application:
    engine: AsyncEngine
    identity: IdentityModule
    establishments: EstablishmentsModule
    cameras: CamerasModule
    analysis: AnalysisModule
    incidents: IncidentsModule
    notifications: NotificationsModule
    directory: DirectoryModule
    event_hub: EventHub


def _scene_analyzer(settings: Settings) -> SceneAnalyzer:
    if not settings.gemini_api_key:
        return DisabledSceneAnalyzer()
    return GeminiSceneAnalyzer(
        settings.gemini_api_key, settings.gemini_model, settings.gemini_media_resolution
    )


def _directory_agent(settings: Settings) -> DirectoryAgent:
    if not settings.gemini_api_key:
        return DisabledDirectoryAgent()
    return GeminiDirectoryAgent(settings.gemini_api_key, settings.gemini_model)


def _wire_events(bus: EventBus, app: Application) -> None:
    """Los módulos no se conocen entre sí: aquí se conectan sus eventos."""
    live = LiveEventPublisher(app.event_hub)

    async def on_delivered(event: AlertDelivered) -> None:
        await app.incidents.record_delivery.delivered(event.incident_id)

    async def on_failed(event: AlertFailed) -> None:
        await app.incidents.record_delivery.failed(event.incident_id)

    bus.subscribe(CameraStatusChanged, app.analysis.supervisor.on_camera_status)
    bus.subscribe(CameraStatusChanged, live.on_camera_status)
    bus.subscribe(SituationDetected, app.incidents.record_situation.execute_event)
    bus.subscribe(IncidentChanged, live.on_incident_changed)
    bus.subscribe(IncidentChanged, app.notifications.push_new_incident.execute)
    # Única conexión hacia WhatsApp: exige un incidente confirmado por un operador.
    bus.subscribe(IncidentConfirmed, app.notifications.deliver_alert.execute)
    bus.subscribe(AlertDelivered, on_delivered)
    bus.subscribe(AlertFailed, on_failed)


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
    analysis = AnalysisModule(
        cameras.frames, cameras.get, _scene_analyzer(settings), settings, bus, clock
    )
    incidents = IncidentsModule(
        sessions,
        FileEvidenceStore(str(Path(settings.media_root) / "evidence")),
        establishments.get,
        bus,
        clock,
        timedelta(days=settings.evidence_retention_days),
    )
    notifications = NotificationsModule(
        sessions,
        establishments.get,
        WhatsAppCloudSender(
            settings.whatsapp_access_token,
            settings.whatsapp_phone_number_id,
            settings.whatsapp_template_name,
            settings.whatsapp_template_language,
            settings.whatsapp_api_version,
        ),
        VapidPushSender(settings.vapid_private_key, settings.vapid_subject),
        bus,
        clock,
    )
    directory = DirectoryModule(
        sessions,
        _directory_agent(settings),
        PoliteFetcher(),
        FileMediaStore(str(Path(settings.media_root) / "directory")),
        NextRevalidator(settings.frontend_internal_url, settings.revalidate_secret),
        clock,
    )
    application = Application(
        engine=engine,
        identity=identity,
        establishments=establishments,
        cameras=cameras,
        analysis=analysis,
        incidents=incidents,
        notifications=notifications,
        directory=directory,
        event_hub=EventHub(),
    )
    _wire_events(bus, application)
    return application
