"""Raíz de composición: el único lugar que conoce las implementaciones concretas."""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from bandit.analysis.domain.models import AnalysisActivity, SituationDetected
from bandit.analysis.domain.ports import SceneAnalyzer
from bandit.analysis.infrastructure.gemini_analyzer import (
    DisabledSceneAnalyzer,
    GeminiSceneAnalyzer,
)
from bandit.analysis.infrastructure.pillow_motion import PillowMotionDetector
from bandit.analysis.module import AnalysisModule
from bandit.cameras.application.discovery import PathAdvisor
from bandit.cameras.domain.models import CameraStatusChanged
from bandit.cameras.infrastructure import tables as camera_tables  # noqa: F401
from bandit.cameras.infrastructure.fernet_cipher import FernetUrlCipher
from bandit.cameras.infrastructure.ffmpeg_source import FfmpegFrameSource
from bandit.cameras.infrastructure.gemini_path_advisor import (
    DisabledPathAdvisor,
    GeminiPathAdvisor,
)
from bandit.cameras.infrastructure.imou_cloud import ImouCloudResolver
from bandit.cameras.infrastructure.resolving_source import ResolvingFrameSource
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
from bandit.establishments.infrastructure.nominatim import NominatimGeocoder
from bandit.establishments.module import EstablishmentsModule
from bandit.faces.application.watcher import FacePolicy
from bandit.faces.domain.models import FaceCheckDone
from bandit.faces.infrastructure.gemini_comparer import GeminiFaceComparer
from bandit.faces.infrastructure.reference_folder import ReferenceFolderWatchList
from bandit.faces.module import FacesModule
from bandit.identity.infrastructure import tables as identity_tables  # noqa: F401
from bandit.identity.module import IdentityModule
from bandit.incidents.domain.models import Incident, IncidentChanged, IncidentConfirmed
from bandit.incidents.infrastructure import tables as incident_tables  # noqa: F401
from bandit.incidents.infrastructure.file_evidence import FileEvidenceStore
from bandit.incidents.module import IncidentsModule
from bandit.notifications.domain.models import AlertDelivered, AlertFailed
from bandit.notifications.infrastructure import tables as notification_tables  # noqa: F401
from bandit.notifications.infrastructure.web_push import VapidPushSender
from bandit.notifications.infrastructure.whatsapp_cloud import WhatsAppCloudSender
from bandit.notifications.module import NotificationsModule
from bandit.places.infrastructure.fallback import FirstAvailableStations
from bandit.places.infrastructure.nominatim_police import NominatimPoliceStations
from bandit.places.infrastructure.osm_tiles import CachedOsmTiles
from bandit.places.infrastructure.overpass import OverpassPoliceStations
from bandit.places.module import PlacesModule
from bandit.realtime.application.event_hub import EventHub
from bandit.realtime.application.translators import LiveEventPublisher
from bandit.shared.background import BackgroundTasks
from bandit.shared.clock import Clock, SystemClock
from bandit.shared.config import Settings
from bandit.shared.db import create_engine, create_session_factory
from bandit.shared.events import EventBus, InMemoryEventBus
from bandit.shared.gemini import model_list


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
    faces: FacesModule
    places: PlacesModule
    event_hub: EventHub
    background: BackgroundTasks


class _EstablishmentCreator:
    """Adapta el módulo de locales al puerto que necesita identidad."""

    def __init__(self, establishments: EstablishmentsModule) -> None:
        self._establishments = establishments

    async def create(self, name: str, address: str) -> UUID:
        return (await self._establishments.create.execute(name, address)).id


def _scene_analyzer(settings: Settings) -> SceneAnalyzer:
    if not settings.gemini_api_key:
        return DisabledSceneAnalyzer()
    return GeminiSceneAnalyzer(
        settings.gemini_api_key,
        settings.gemini_model,
        settings.gemini_media_resolution,
        fallback_models=model_list(
            settings.gemini_directory_model, settings.gemini_fallback_models
        ),
    )


def _text_model(settings: Settings) -> str:
    """Modelo para tareas de texto: extraer el directorio y sugerir rutas de cámaras."""
    return settings.gemini_directory_model or settings.gemini_model


def _path_advisor(settings: Settings) -> PathAdvisor:
    if not settings.gemini_api_key:
        return DisabledPathAdvisor()
    return GeminiPathAdvisor(settings.gemini_api_key, _text_model(settings))


def _directory_agent(settings: Settings) -> DirectoryAgent:
    if not settings.gemini_api_key:
        return DisabledDirectoryAgent()
    return GeminiDirectoryAgent(settings.gemini_api_key, _text_model(settings))


def _faces_module(
    settings: Settings,
    cameras: CamerasModule,
    directory: DirectoryModule,
    bus: EventBus,
    clock: Clock,
) -> FacesModule:
    async def consented_people() -> list[tuple[str, str]]:
        records = await directory.list_active.execute()
        return [(record.name, record.slug) for record in records if record.local_test]

    enabled = settings.face_watch_enabled and bool(settings.gemini_api_key)
    return FacesModule(
        cameras.frames,
        cameras.get,
        GeminiFaceComparer(
            settings.gemini_api_key,
            model_list(settings.face_watch_model, settings.gemini_fallback_models),
        )
        if enabled
        else None,
        ReferenceFolderWatchList(str(Path(settings.media_root) / "faces"), consented_people),
        PillowMotionDetector(),
        FacePolicy(
            min_interval_seconds=settings.face_watch_interval_seconds,
            motion_threshold=settings.analysis_motion_threshold,
        ),
        settings.face_watch_cooldown_seconds,
        settings.face_watch_daily_limit,
        bus,
        clock,
    )


def _wire_events(bus: EventBus, app: Application) -> None:
    """Los módulos no se conocen entre sí: aquí se conectan sus eventos."""
    live = LiveEventPublisher(app.event_hub)

    async def on_confirmed(event: IncidentConfirmed) -> None:
        # Los reintentos pueden tardar: el operador no debe quedar esperando.
        app.background.spawn(app.notifications.deliver_alert.execute(event))

    async def on_delivered(event: AlertDelivered) -> None:
        await app.incidents.record_delivery.delivered(event.incident_id)

    async def on_failed(event: AlertFailed) -> None:
        await app.incidents.record_delivery.failed(event.incident_id)

    bus.subscribe(CameraStatusChanged, app.analysis.supervisor.on_camera_status)
    bus.subscribe(CameraStatusChanged, live.on_camera_status)
    bus.subscribe(AnalysisActivity, live.on_analysis_activity)
    bus.subscribe(SituationDetected, app.incidents.record_situation.execute_event)
    bus.subscribe(IncidentChanged, live.on_incident_changed)
    bus.subscribe(IncidentChanged, app.notifications.push_new_incident.execute)
    # Única conexión hacia WhatsApp: exige un incidente confirmado por un operador.
    bus.subscribe(IncidentConfirmed, on_confirmed)
    bus.subscribe(AlertDelivered, on_delivered)
    bus.subscribe(AlertFailed, on_failed)

    # Prueba de rostros: cada comparación va a Actividad; una coincidencia, a Eventos.
    async def on_face_check(event: FaceCheckDone) -> None:
        check = event.check
        if not check.alerted or check.person is None:
            return
        incident = Incident(
            id=uuid4(),
            establishment_id=check.establishment_id,
            camera_id=check.camera_id,
            camera_name=check.camera_name,
            type=WANTED_MATCH,
            severity="high",
            confidence=check.confidence,
            description=describe_face_match(check.person, check.confidence, check.explanation),
            detected_at=check.at,
        )
        await app.incidents.record_situation.record(incident, event.jpeg)

    if app.faces.supervisor is not None:
        bus.subscribe(CameraStatusChanged, app.faces.supervisor.on_camera_status)
    bus.subscribe(FaceCheckDone, live.on_face_check)
    bus.subscribe(FaceCheckDone, on_face_check)


WANTED_MATCH = "wanted_match"


def describe_face_match(person: str, confidence: float, explanation: str) -> str:
    text = (
        f"Coincidencia con {person}, de la lista de buscados (registro de prueba), "
        f"{confidence:.0%}: {explanation}"
    )
    return text[:300]


def build_application(settings: Settings) -> Application:
    engine = create_engine(settings.database_url)
    sessions = create_session_factory(engine)
    clock = SystemClock()
    bus = InMemoryEventBus()

    establishments = EstablishmentsModule(sessions, NominatimGeocoder(settings.osm_user_agent))
    identity = IdentityModule(
        sessions,
        clock,
        timedelta(hours=settings.session_ttl_hours),
        settings.cookie_secure,
        _EstablishmentCreator(establishments),
        settings.demo_admin,
    )
    imou = ImouCloudResolver(settings.imou_app_id, settings.imou_app_secret, settings.imou_api_url)
    cameras = CamerasModule(
        sessions,
        ResolvingFrameSource(
            FfmpegFrameSource(settings.ffmpeg_path, settings.video_fps, settings.video_width),
            imou,
        ),
        FernetUrlCipher(settings.camera_encryption_key),
        bus,
        clock,
        _path_advisor(settings),
        imou,
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
        timedelta(hours=settings.directory_scrape_interval_hours),
        settings.smlmv_cop,
    )
    faces = _faces_module(settings, cameras, directory, bus, clock)
    application = Application(
        engine=engine,
        identity=identity,
        establishments=establishments,
        cameras=cameras,
        analysis=analysis,
        incidents=incidents,
        notifications=notifications,
        directory=directory,
        faces=faces,
        places=PlacesModule(
            FirstAvailableStations(
                [
                    NominatimPoliceStations(settings.osm_user_agent),
                    OverpassPoliceStations(settings.osm_user_agent),
                ]
            ),
            CachedOsmTiles(str(Path(settings.media_root) / "tiles"), settings.osm_user_agent),
        ),
        event_hub=EventHub(),
        background=BackgroundTasks(),
    )
    _wire_events(bus, application)
    return application
