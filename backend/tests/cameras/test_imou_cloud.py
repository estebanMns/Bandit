"""La nube de Imou entrega el video HLS de una cámara que la red local no alcanza."""

import hashlib
import json

import httpx
import pytest

from bandit.cameras.domain.models import validate_stream_url
from bandit.cameras.infrastructure.imou_cloud import ImouCloudError, ImouCloudResolver
from bandit.cameras.infrastructure.resolving_source import ResolvingFrameSource
from bandit.shared.errors import InvalidDataError

SECRET = "secreto-de-prueba"
HLS_HTTP = "http://cdn.example.com/live/dev_ABC123_1.m3u8"
HLS_HTTPS = "https://cdn.example.com/live/dev_ABC123_1.m3u8?proto=https"


def ok(data):
    return {"result": {"code": "0", "msg": "ok", "data": data}, "id": "1"}


def fail(code):
    return {"result": {"code": code, "msg": "error"}, "id": "1"}


class FakeImou:
    """Simula la Open Platform: guarda cada llamada y responde por guion."""

    def __init__(self, live=None, bind=None):
        self.calls: list[tuple[str, dict]] = []
        self.live = live or [ok({"streams": [{"streamId": 1, "hls": HLS_HTTP, "status": "1"}]})]
        self.bind = bind or ok({"liveToken": "t"})
        self.tokens = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        method = request.url.path.rsplit("/", 1)[-1]
        body = json.loads(request.content)
        self.calls.append((method, body))
        if method == "accessToken":
            self.tokens += 1
            return httpx.Response(
                200, json=ok({"accessToken": f"tk{self.tokens}", "expireTime": 259200})
            )
        if method == "getLiveStreamInfo":
            return httpx.Response(
                200, json=self.live.pop(0) if len(self.live) > 1 else self.live[0]
            )
        if method == "bindDeviceLive":
            return httpx.Response(200, json=self.bind)
        return httpx.Response(404)

    def resolver(self):
        return ImouCloudResolver(
            "app", SECRET, "https://imou.example.com/openapi", httpx.MockTransport(self.handler)
        )

    def methods(self):
        return [method for method, _ in self.calls]


async def test_every_request_is_signed_without_exposing_the_secret():
    imou = FakeImou()

    await imou.resolver().resolve("imou://ABC123/0?stream=1")

    for _, body in imou.calls:
        system = body["system"]
        expected = f"time:{system['time']},nonce:{system['nonce']},appSecret:{SECRET}"
        assert system["sign"] == hashlib.md5(expected.encode(), usedforsecurity=False).hexdigest()
        assert SECRET not in json.dumps(body)


async def test_existing_live_address_is_reused():
    imou = FakeImou()

    url = await imou.resolver().resolve("imou://ABC123/0?stream=1")

    assert url == HLS_HTTP
    assert imou.methods() == ["accessToken", "getLiveStreamInfo"]
    params = imou.calls[1][1]["params"]
    assert (params["deviceId"], params["channelId"], params["token"]) == ("ABC123", "0", "tk1")


async def test_missing_live_address_is_created_first():
    imou = FakeImou(live=[fail("LV1002"), ok({"streams": [{"streamId": 1, "hls": HLS_HTTP}]})])

    assert await imou.resolver().resolve("imou://ABC123/1?stream=1") == HLS_HTTP
    assert imou.methods() == [
        "accessToken",
        "getLiveStreamInfo",
        "bindDeviceLive",
        "getLiveStreamInfo",
    ]
    assert imou.calls[2][1]["params"]["streamId"] == 1


async def test_already_existing_address_is_not_an_error():
    imou = FakeImou(
        live=[ok({"streams": []}), ok({"streams": [{"streamId": 1, "hls": HLS_HTTP}]})],
        bind=fail("LV1001"),
    )

    assert await imou.resolver().resolve("imou://ABC123/0") == HLS_HTTP


async def test_prefers_requested_quality_switched_on_and_https():
    streams = [
        {"streamId": 0, "hls": "https://cdn.example.com/hd.m3u8", "status": "1"},
        {"streamId": 1, "hls": HLS_HTTP, "status": "1"},
        {"streamId": 1, "hls": "https://cdn.example.com/off.m3u8", "status": "10"},
        {"streamId": 1, "hls": HLS_HTTPS, "status": "1"},
    ]
    imou = FakeImou(live=[ok({"streams": streams})])

    assert await imou.resolver().resolve("imou://ABC123/0?stream=1") == HLS_HTTPS


async def test_token_is_reused_and_renewed_when_expired():
    imou = FakeImou(live=[fail("TK1002"), ok({"streams": [{"streamId": 1, "hls": HLS_HTTP}]})])
    resolver = imou.resolver()

    await resolver.resolve("imou://ABC123/0")
    await resolver.resolve("imou://ABC123/0")

    assert imou.tokens == 2
    assert imou.methods().count("accessToken") == 2


async def test_device_errors_are_reported_with_their_code():
    imou = FakeImou(live=[fail("DV1007")])

    with pytest.raises(ImouCloudError) as error:
        await imou.resolver().resolve("imou://ABC123/0")
    assert error.value.code == "DV1007"


async def test_missing_credentials_fail_clearly():
    resolver = ImouCloudResolver("", "", "https://imou.example.com/openapi")

    with pytest.raises(ImouCloudError, match="IMOU_APP_ID"):
        await resolver.resolve("imou://ABC123/0")


class RecordingSource:
    def __init__(self):
        self.urls: list[str] = []

    async def stream(self, url):
        self.urls.append(url)
        yield b"jpeg"


async def test_rtsp_goes_straight_and_imou_is_resolved_first():
    inner = RecordingSource()
    source = ResolvingFrameSource(inner, FakeImou().resolver())

    for url in ("rtsp://10.0.0.9/stream", "imou://ABC123/0?stream=1"):
        assert [frame async for frame in source.stream(url)] == [b"jpeg"]

    assert inner.urls == ["rtsp://10.0.0.9/stream", HLS_HTTP]


@pytest.mark.parametrize(
    "url",
    ["imou://ABC123/0", "imou://ABC123/1?stream=0", "rtsp://10.0.0.9/stream"],
)
def test_valid_camera_urls(url):
    assert validate_stream_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "imou://",
        "imou://ABC123/canal",
        "imou://ABC123/0?stream=5",
        "imou://ABC-123/0",
        "http://x/y",
    ],
)
def test_invalid_camera_urls(url):
    with pytest.raises(InvalidDataError):
        validate_stream_url(url)
