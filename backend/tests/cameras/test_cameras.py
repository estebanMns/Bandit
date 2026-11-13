import asyncio
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from bandit.cameras.domain.models import CameraStatus, CameraStatusChanged, validate_stream_url
from bandit.cameras.infrastructure.fernet_cipher import FernetUrlCipher
from bandit.cameras.infrastructure.gemini_path_advisor import DisabledPathAdvisor
from bandit.cameras.infrastructure.imou_cloud import ImouCloudResolver
from bandit.cameras.module import CamerasModule
from bandit.establishments.module import EstablishmentsModule
from bandit.shared.errors import InvalidDataError
from bandit.shared.events import InMemoryEventBus

URL = "rtsp://admin:secreto@192.168.1.20:554/stream"


class ScriptedSource:
    """Doble de prueba: cada conexión reproduce el siguiente guion."""

    def __init__(self, *scripts):
        self.scripts = list(scripts)
        self.urls: list[str] = []

    async def stream(self, url):
        self.urls.append(url)
        script = self.scripts.pop(0) if self.scripts else None
        if script is None:
            await asyncio.Event().wait()
        for item in script:
            if isinstance(item, Exception):
                raise item
            yield item
        if not self.scripts:
            await asyncio.Event().wait()


@pytest.fixture
def cipher() -> FernetUrlCipher:
    return FernetUrlCipher(Fernet.generate_key().decode())


@pytest.fixture
async def establishment(sessions):
    return await EstablishmentsModule(sessions).create.execute("Bar", "Calle 1")


def build(sessions, source, cipher, clock, bus=None) -> CamerasModule:
    return CamerasModule(
        sessions,
        source,
        cipher,
        bus or InMemoryEventBus(),
        clock,
        DisabledPathAdvisor(),
        ImouCloudResolver("", "", "https://imou.invalid/openapi"),
    )


async def wait_until(condition) -> None:
    async with asyncio.timeout(2):
        while not condition():
            await asyncio.sleep(0.001)


@pytest.mark.parametrize("url", ["rtsp://10.0.0.1/a", "RTSPS://camara.local:322/b"])
def test_accepts_rtsp_urls(url):
    assert validate_stream_url(url) == url


@pytest.mark.parametrize(
    "url", ["http://10.0.0.1/a", "file:///etc/passwd", "rtsp://", "-i rtsp://x", ""]
)
def test_rejects_other_urls(url):
    with pytest.raises(InvalidDataError):
        validate_stream_url(url)


async def test_url_is_stored_encrypted(sessions, cipher, clock, establishment):
    module = build(sessions, ScriptedSource(), cipher, clock)

    camera = await module.register.execute(establishment.id, "Barra", URL)
    await module.supervisor.stop_all()

    assert "secreto" not in camera.encrypted_url
    assert cipher.decrypt((await module.get.execute(camera.id)).encrypted_url) == URL


async def test_frames_fan_out_to_every_subscriber(sessions, cipher, clock, establishment):
    source = ScriptedSource([b"uno"])
    module = build(sessions, source, cipher, clock)
    camera_id_box = {}

    original_start = module.supervisor.start

    def capture_id(camera):
        camera_id_box["id"] = camera.id
        viewers.extend([module.frames.subscribe(camera.id), module.frames.subscribe(camera.id)])
        original_start(camera)

    viewers: list = []
    module.supervisor.start = capture_id
    await module.register.execute(establishment.id, "Barra", URL)
    await wait_until(lambda: viewers and not viewers[0]._queue.empty())
    await wait_until(lambda: not viewers[1]._queue.empty())

    assert viewers[0]._queue.get_nowait().jpeg == b"uno"
    assert viewers[1]._queue.get_nowait().jpeg == b"uno"
    await module.supervisor.stop_all()


async def test_supervisor_reconnects_after_a_failure(sessions, cipher, clock, establishment):
    source = ScriptedSource([ConnectionError("rtsp://admin:secreto@caida")], [b"dos"])
    bus = InMemoryEventBus()
    statuses: list[CameraStatus] = []

    async def record(event: CameraStatusChanged) -> None:
        statuses.append(event.status)

    bus.subscribe(CameraStatusChanged, record)
    module = build(sessions, source, cipher, clock, bus)
    module.supervisor._initial_backoff = 0.001

    await module.register.execute(establishment.id, "Barra", URL)
    await wait_until(lambda: CameraStatus.LIVE in statuses)
    await module.supervisor.stop_all()

    assert statuses[:4] == [
        CameraStatus.CONNECTING,
        CameraStatus.RETRYING,
        CameraStatus.CONNECTING,
        CameraStatus.LIVE,
    ]


async def test_disabling_a_camera_stops_capture(sessions, cipher, clock, establishment):
    module = build(sessions, ScriptedSource(), cipher, clock)
    camera = await module.register.execute(establishment.id, "Barra", URL)

    updated = await module.set_enabled.execute(camera.id, False)

    assert updated.enabled is False
    assert module.supervisor.status_of(camera.id) is CameraStatus.STOPPED


async def test_failure_logs_do_not_leak_credentials(sessions, cipher, clock, establishment, caplog):
    source = ScriptedSource([ConnectionError("rtsp://admin:secreto@caida")], [b"dos"])
    module = build(sessions, source, cipher, clock)
    module.supervisor._initial_backoff = 0.001

    await module.register.execute(establishment.id, "Barra", URL)
    await wait_until(lambda: len(source.urls) == 2)
    await module.supervisor.stop_all()

    assert "secreto" not in caplog.text


async def test_unknown_camera_id_is_not_found(sessions, cipher, clock):
    from bandit.shared.errors import NotFoundError

    module = build(sessions, ScriptedSource(), cipher, clock)

    with pytest.raises(NotFoundError):
        await module.get.execute(uuid4())


async def test_a_camera_saved_with_another_key_stops_with_a_clear_message(
    sessions, cipher, clock, establishment, caplog
):
    await build(sessions, ScriptedSource(), cipher, clock).register.execute(
        establishment.id, "Barra", URL
    )
    await asyncio.sleep(0)
    other_key = FernetUrlCipher(Fernet.generate_key().decode())
    source = ScriptedSource()
    module = build(sessions, source, other_key, clock)

    await module.supervisor.start_all()
    await asyncio.sleep(0.01)

    camera = (await module.list_for.execute(establishment.id))[0]
    assert module.supervisor.status_of(camera.id) is CameraStatus.STOPPED
    assert source.urls == []
    assert "CAMERA_ENCRYPTION_KEY" in caplog.text
    assert "secreto" not in caplog.text


async def test_cameras_added_or_disabled_from_another_computer_are_followed(
    sessions, cipher, clock, establishment
):
    # Dos backends sobre la misma base, como el PC y la Mac.
    here = build(sessions, ScriptedSource(), cipher, clock)
    other = build(sessions, ScriptedSource(), cipher, clock)
    camera = await other.register.execute(establishment.id, "Barra", URL)
    await other.supervisor.stop_all()

    await here.supervisor.reconcile()
    await wait_until(lambda: here.supervisor.status_of(camera.id) is not CameraStatus.STOPPED)

    await other.set_enabled.execute(camera.id, False)
    await here.supervisor.reconcile()

    assert here.supervisor.status_of(camera.id) is CameraStatus.STOPPED
    await here.supervisor.stop_all()
    await other.supervisor.stop_all()


async def test_an_unreadable_camera_is_not_retried_every_minute(
    sessions, cipher, clock, establishment, caplog
):
    await build(sessions, ScriptedSource(), cipher, clock).register.execute(
        establishment.id, "Barra", URL
    )
    source = ScriptedSource()
    module = build(sessions, source, FernetUrlCipher(Fernet.generate_key().decode()), clock)

    for _ in range(3):
        await module.supervisor.reconcile()
        await asyncio.sleep(0.01)

    assert caplog.text.count("CAMERA_ENCRYPTION_KEY") == 1
    assert source.urls == []
