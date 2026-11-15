"""Cada cliente conecta su cámara Imou con serie + clave, y ningún local ve las de otro."""

import asyncio
import json

import httpx
import pytest
from cryptography.fernet import Fernet

from bandit.cameras.application.imou_connect import MAX_FAILURES, normalize_serial
from bandit.cameras.infrastructure.fernet_cipher import FernetUrlCipher
from bandit.cameras.infrastructure.gemini_path_advisor import DisabledPathAdvisor
from bandit.cameras.infrastructure.imou_cloud import ImouCloudResolver, bind_error
from bandit.cameras.module import CamerasModule
from bandit.establishments.module import EstablishmentsModule
from bandit.shared.errors import (
    ConflictError,
    InvalidDataError,
    PermissionDeniedError,
    RateLimitedError,
    UnavailableError,
)
from bandit.shared.events import InMemoryEventBus

SERIAL = "ABC123XYZ"
CODE = "L2B7C9X1"
LEGACY = "OTRA1234"


class IdleSource:
    async def stream(self, url):
        await asyncio.Event().wait()
        yield b""


class FakeImou:
    """La Open Platform de Imou: vincula con la clave correcta y lista las cámaras vinculadas."""

    def __init__(self):
        self.bound: set[str] = {LEGACY}
        self.binds = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[-1]
        params = json.loads(request.content)["params"]
        if method == "accessToken":
            return self._ok({"accessToken": "t", "expireTime": 9999})
        if method == "bindDevice":
            self.binds += 1
            if params["deviceId"] in self.bound:
                return self._error("DV1003")
            if params["code"] != CODE:
                return self._error("DV1005")
            self.bound.add(params["deviceId"])
            return self._ok({})
        devices = [
            {
                "deviceId": device,
                "deviceName": "Cruiser",
                "channelList": [{"channelId": "0"}, {"channelId": "1"}],
            }
            for device in sorted(self.bound)
        ]
        return self._ok({"deviceList": devices})

    @staticmethod
    def _ok(data):
        return httpx.Response(200, json={"result": {"code": "0", "data": data}})

    @staticmethod
    def _error(code):
        return httpx.Response(200, json={"result": {"code": code, "msg": "x"}})


@pytest.fixture
def imou():
    return FakeImou()


@pytest.fixture
def module(sessions, clock, imou):
    cloud = ImouCloudResolver(
        "app", "secreto", "https://imou.example/openapi", httpx.MockTransport(imou.handler)
    )
    return CamerasModule(
        sessions,
        IdleSource(),
        FernetUrlCipher(Fernet.generate_key().decode()),
        InMemoryEventBus(),
        clock,
        DisabledPathAdvisor(),
        cloud,
        capture_enabled=False,
    )


@pytest.fixture
async def locales(sessions):
    establishments = EstablishmentsModule(sessions)
    first = await establishments.create.execute("Bar", "Calle 1")
    second = await establishments.create.execute("Tienda", "Calle 2")
    return first.id, second.id


def test_the_serial_is_read_as_on_the_label():
    assert normalize_serial(" abc-123 xyz ") == SERIAL
    with pytest.raises(InvalidDataError):
        normalize_serial("ABC/123")


async def test_serial_and_code_connect_every_lens(module, locales):
    first, _ = locales

    result = await module.connect_imou.execute(first, "abc123xyz", CODE)

    assert len(result.added) == 2
    assert len(await module.list_for.execute(first)) == 2
    again = await module.connect_imou.execute(first, SERIAL, CODE)
    assert again.added == []
    assert again.already == 2


async def test_a_wrong_code_is_explained_and_attempts_are_limited(module, locales, imou):
    first, _ = locales

    for _ in range(MAX_FAILURES):
        with pytest.raises(InvalidDataError, match="clave"):
            await module.connect_imou.execute(first, SERIAL, "000000")
    with pytest.raises(RateLimitedError):
        await module.connect_imou.execute(first, SERIAL, CODE)

    assert imou.binds == MAX_FAILURES
    assert await module.list_for.execute(first) == []


async def test_a_camera_belongs_to_a_single_establishment(module, locales):
    first, second = locales
    await module.connect_imou.execute(first, SERIAL, CODE)

    with pytest.raises(ConflictError):
        await module.connect_imou.execute(second, SERIAL, CODE)
    assert await module.list_for.execute(second) == []


async def test_the_cloud_button_only_brings_cameras_of_this_establishment(module, locales):
    first, second = locales
    await module.connect_imou.execute(first, SERIAL, CODE)

    result = await module.auto_connect.execute(second, None, "admin", "")

    assert not result.connected
    assert await module.list_for.execute(second) == []


async def test_an_imou_address_typed_by_hand_must_belong_to_the_establishment(module, locales):
    first, second = locales
    await module.connect_imou.execute(first, SERIAL, CODE)

    await module.imou_ownership.ensure(first, f"imou://{SERIAL}/0?stream=0")
    await module.imou_ownership.ensure(second, "rtsp://admin:x@192.168.1.5/stream")
    with pytest.raises(PermissionDeniedError, match="otro local"):
        await module.imou_ownership.ensure(second, f"imou://{SERIAL}/0?stream=1")
    with pytest.raises(PermissionDeniedError, match="número de serie"):
        await module.imou_ownership.ensure(second, f"imou://{LEGACY}/0?stream=1")


async def test_cameras_saved_before_keep_working_for_their_establishment(module, locales):
    first, second = locales
    await module.register.execute(first, "Vieja", f"imou://{LEGACY}/0?stream=1")
    await module.register.execute(second, "Copia", f"imou://{LEGACY}/1?stream=1")

    assert await module.adopt_imou.execute() == 1

    # Si dos locales la tenían, se queda con uno solo.
    allowed = []
    for establishment in (first, second):
        try:
            await module.imou_ownership.ensure(establishment, f"imou://{LEGACY}/1?stream=1")
            allowed.append(establishment)
        except PermissionDeniedError:
            pass
    assert len(allowed) == 1
    assert await module.adopt_imou.execute() == 0


def test_unknown_imou_refusals_still_read_well():
    error = bind_error("DV9999")
    assert isinstance(error, UnavailableError)
    assert "DV9999" in str(error)
    assert "Imou Life" in str(bind_error("DV1001"))
