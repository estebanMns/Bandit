"""Convierte imou://<serie>/<canal>?stream=N en la URL HLS que entrega la Open Platform de Imou.

Sirve cuando el equipo de Bandit no alcanza la cámara por la red local: el video llega
por internet desde la nube de Imou. Documentación: https://open.imoulife.com
"""

import hashlib
import secrets
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit

import httpx

_TOKEN_MARGIN_SECONDS = 300
_LIVE_ALREADY_EXISTS = "LV1001"
_LIVE_MISSING = {"LV1002", "LV1005"}
_TOKEN_EXPIRED = "TK1002"  # noqa: S105  Es un código de error, no una clave.
_STREAM_ON = "1"


class ImouCloudError(Exception):
    """La nube de Imou rechazó la petición. El código nunca incluye secretos."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True, slots=True)
class ImouTarget:
    device_id: str
    channel_id: str
    stream_id: int

    @classmethod
    def parse(cls, url: str) -> "ImouTarget":
        parts = urlsplit(url)
        stream = parse_qs(parts.query).get("stream", ["1"])[0]
        return cls(parts.netloc, parts.path.strip("/"), int(stream))


_PAGE_SIZE = 50
_MAX_PAGES = 5
_ONLINE = {"online", "1", "true"}


@dataclass(frozen=True, slots=True)
class ImouCamera:
    """Un canal (lente) de una cámara de la cuenta de Imou."""

    device_id: str
    device_name: str
    channel_id: str
    channel_name: str
    online: bool

    @property
    def url(self) -> str:
        return f"imou://{self.device_id}/{self.channel_id}?stream=1"


def _text(item: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _is_online(item: dict[str, object], *keys: str) -> bool:
    status = _text(item, *keys).lower()
    return not status or status in _ONLINE


def cameras_from_page(data: dict[str, object]) -> list[ImouCamera]:
    """Lee con tolerancia la respuesta de device.detail.page."""
    found: list[ImouCamera] = []
    devices = data.get("deviceList") or data.get("devices") or []
    for device in devices if isinstance(devices, list) else []:
        if not isinstance(device, dict):
            continue
        device_id = _text(device, "deviceId", "deviceID")
        device_name = _text(device, "deviceName", "name") or device_id
        device_online = _is_online(device, "deviceStatus", "status")
        channels = device.get("channelList") or device.get("channels") or [{"channelId": "0"}]
        for channel in channels if isinstance(channels, list) else []:
            if not isinstance(channel, dict) or not device_id:
                continue
            channel_id = _text(channel, "channelId", "channelID") or "0"
            found.append(
                ImouCamera(
                    device_id=device_id,
                    device_name=device_name,
                    channel_id=channel_id,
                    channel_name=_text(channel, "channelName", "name")
                    or f"Canal {int(channel_id) + 1 if channel_id.isdigit() else channel_id}",
                    online=device_online and _is_online(channel, "channelStatus", "status"),
                )
            )
    return found


class ImouCloudResolver:
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        api_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._api_url = api_url.rstrip("/")
        self._transport = transport
        self._token: str | None = None
        self._token_expires = 0.0

    @property
    def configured(self) -> bool:
        return bool(self._app_id and self._app_secret)

    async def list_cameras(self) -> list[ImouCamera]:
        """Todas las cámaras de la cuenta de Imou, un elemento por canal."""
        if not self.configured:
            raise ImouCloudError("CONFIG", "Faltan IMOU_APP_ID e IMOU_APP_SECRET")
        cameras: list[ImouCamera] = []
        async with httpx.AsyncClient(transport=self._transport, timeout=20) as client:
            for page in range(1, _MAX_PAGES + 1):
                data = await self._call(
                    client,
                    "v2/device.detail.page",
                    {"page": page, "pageSize": _PAGE_SIZE, "source": "bindAndShare"},
                )
                batch = cameras_from_page(data)
                cameras.extend(batch)
                devices = data.get("deviceList")
                if not isinstance(devices, list) or len(devices) < _PAGE_SIZE:
                    break
        return cameras

    async def resolve(self, url: str) -> str:
        if not self.configured:
            raise ImouCloudError("CONFIG", "Faltan IMOU_APP_ID e IMOU_APP_SECRET")
        target = ImouTarget.parse(url)
        async with httpx.AsyncClient(transport=self._transport, timeout=20) as client:
            streams = await self._live_streams(client, target)
            if not streams:
                await self._bind(client, target)
                streams = await self._live_streams(client, target)
        return self._pick(streams, target.stream_id)

    async def _live_streams(
        self, client: httpx.AsyncClient, target: ImouTarget
    ) -> list[dict[str, object]]:
        try:
            data = await self._call(
                client,
                "getLiveStreamInfo",
                {"deviceId": target.device_id, "channelId": target.channel_id},
            )
        except ImouCloudError as error:
            if error.code in _LIVE_MISSING:
                return []
            raise
        streams = data.get("streams")
        return streams if isinstance(streams, list) else []

    async def _bind(self, client: httpx.AsyncClient, target: ImouTarget) -> None:
        try:
            await self._call(
                client,
                "bindDeviceLive",
                {
                    "deviceId": target.device_id,
                    "channelId": target.channel_id,
                    "streamId": target.stream_id,
                },
            )
        except ImouCloudError as error:
            if error.code != _LIVE_ALREADY_EXISTS:
                raise

    @staticmethod
    def _pick(streams: list[dict[str, object]], stream_id: int) -> str:
        """Prefiere la calidad pedida, encendida y por HTTPS."""

        def score(stream: dict[str, object]) -> tuple[bool, bool, bool]:
            hls = str(stream.get("hls", ""))
            return (
                stream.get("streamId", stream_id) == stream_id,
                str(stream.get("status", _STREAM_ON)) == _STREAM_ON,
                hls.startswith("https://"),
            )

        candidates = [s for s in streams if s.get("hls")]
        if not candidates:
            raise ImouCloudError("NO_STREAM", "La nube no devolvió un video en vivo")
        return str(max(candidates, key=score)["hls"])

    async def _call(
        self, client: httpx.AsyncClient, method: str, params: dict[str, object]
    ) -> dict[str, object]:
        token = await self._access_token(client)
        try:
            return await self._post(client, method, {**params, "token": token})
        except ImouCloudError as error:
            if error.code != _TOKEN_EXPIRED:
                raise
            self._token = None
            token = await self._access_token(client)
            return await self._post(client, method, {**params, "token": token})

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        if self._token and time.monotonic() < self._token_expires:
            return self._token
        data = await self._post(client, "accessToken", {})
        self._token = str(data["accessToken"])
        lifetime = float(str(data.get("expireTime", 0)))
        self._token_expires = time.monotonic() + max(lifetime - _TOKEN_MARGIN_SECONDS, 0)
        return self._token

    def _system(self) -> dict[str, object]:
        now = int(time.time())
        nonce = secrets.token_hex(16)
        sign = hashlib.md5(
            f"time:{now},nonce:{nonce},appSecret:{self._app_secret}".encode(),
            usedforsecurity=False,
        ).hexdigest()
        return {"ver": "1.0", "appId": self._app_id, "sign": sign, "time": now, "nonce": nonce}

    async def _post(
        self, client: httpx.AsyncClient, method: str, params: dict[str, object]
    ) -> dict[str, object]:
        body = {"system": self._system(), "id": secrets.token_hex(8), "params": params}
        response = await client.post(f"{self._api_url}/{method}", json=body)
        response.raise_for_status()
        result = response.json().get("result", {})
        code = str(result.get("code", ""))
        if code != "0":
            raise ImouCloudError(code or "UNKNOWN", str(result.get("msg", "")))
        data = result.get("data") or {}
        return data if isinstance(data, dict) else {}
