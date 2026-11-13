"""Conectar por el medio que funcione: primero la red local, luego la nube de Imou."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

import httpx

from bandit.cameras.application.auto_connect import AttemptStatus, AutoConnect, Method
from bandit.cameras.application.discovery import ConnectDevice, ScanNetwork
from bandit.cameras.domain.discovery import DiscoveredDevice
from bandit.cameras.infrastructure.imou_cloud import ImouCloudResolver, cameras_from_page

CAMERA = DiscoveredDevice("192.168.1.102", (554, 37777), "Dahua / Imou")
ROUTER = DiscoveredDevice("192.168.1.1", (80,), None)
LENS = "/cam/realmonitor?channel={}&subtype=1"
SECRET = "codigo-etiqueta"


class Scanner:
    def __init__(self, devices, reachable=True):
        self.devices = devices
        self.reachable = reachable

    async def scan(self, hosts):
        return self.devices

    async def inspect(self, ip):
        return CAMERA if self.reachable else None


class Prober:
    async def describe(self, ip, port, path, username, password):
        if password != SECRET:
            return 401
        return 200 if path in {LENS.format(1), LENS.format(2)} else 404


class Advisor:
    async def suggest(self, device):
        return []


@dataclass(frozen=True)
class FakeCloudCamera:
    url: str
    device_name: str
    channel_name: str
    online: bool = True


class Cloud:
    def __init__(self, configured=True, cameras=()):
        self.configured = configured
        self.cameras = list(cameras)
        self.calls = 0

    async def list_cameras(self):
        self.calls += 1
        return self.cameras


class Registry:
    """Hace de RegisterCamera, ListCameras y del cifrado a la vez."""

    def __init__(self, existing=()):
        self.urls = list(existing)

    async def execute(self, establishment_id, name=None, url=None):
        if url is None:
            return [type("C", (), {"encrypted_url": u})() for u in self.urls]
        self.urls.append(url)

    def decrypt(self, value):
        return value

    def encrypt(self, value):
        return value


def build(clock, scanner, cloud, registry):
    return AutoConnect(
        ScanNetwork(scanner, clock, timedelta(0)),
        ConnectDevice(scanner, Prober(), Advisor()),
        registry,
        registry,
        registry,
        cloud,
    )


async def test_local_network_first_and_cloud_untouched(clock):
    cloud, registry = Cloud(), Registry()
    result = await build(clock, Scanner([CAMERA]), cloud, registry).execute(
        uuid4(), "192.168.1.0/24", "admin", SECRET
    )

    assert len(result.added) == 2
    assert all(
        url.startswith("rtsp://admin:codigo-etiqueta@192.168.1.102:554/") for url in registry.urls
    )
    assert cloud.calls == 0
    assert [a.status for a in result.attempts] == [AttemptStatus.CONNECTED, AttemptStatus.SKIPPED]


async def test_blocked_camera_falls_back_to_the_cloud(clock):
    cloud = Cloud(cameras=[FakeCloudCamera("imou://ABC/0?stream=1", "Cruiser", "Lente 1")])
    registry = Registry()
    result = await build(clock, Scanner([ROUTER]), cloud, registry).execute(
        uuid4(), "192.168.1.0/24", "admin", SECRET
    )

    assert registry.urls == ["imou://ABC/0?stream=1"]
    statuses = {a.method: a.status for a in result.attempts}
    assert statuses == {
        Method.LAN: AttemptStatus.NOTHING_FOUND,
        Method.CLOUD: AttemptStatus.CONNECTED,
    }


async def test_without_cloud_credentials_it_says_what_is_missing(clock):
    result = await build(clock, Scanner([ROUTER]), Cloud(configured=False), Registry()).execute(
        uuid4(), "192.168.1.0/24", "admin", SECRET
    )

    assert not result.connected
    assert result.attempts[-1].status is AttemptStatus.NOT_CONFIGURED
    assert "IMOU_APP_ID" in result.attempts[-1].detail


async def test_never_duplicates_cameras(clock):
    cloud = Cloud(cameras=[FakeCloudCamera("imou://ABC/0?stream=1", "Cruiser", "Lente 1")])
    registry = Registry(existing=["imou://ABC/0?stream=1"])
    result = await build(clock, Scanner([]), cloud, registry).execute(uuid4(), None, "admin", "")

    assert result.added == [] and result.already == 1 and result.connected


async def test_found_cameras_without_password_ask_for_it(clock):
    cloud = Cloud(configured=False)
    result = await build(clock, Scanner([CAMERA]), cloud, Registry()).execute(
        uuid4(), "192.168.1.0/24", "admin", ""
    )

    assert result.attempts[0].status is AttemptStatus.NEEDS_CREDENTIALS


def test_reads_the_imou_device_list_tolerantly():
    data = {
        "deviceList": [
            {
                "deviceId": "ABC123",
                "deviceName": "Cruiser Dual 2",
                "deviceStatus": "online",
                "channelList": [
                    {"channelId": "0", "channelName": "Lente fijo", "channelStatus": "online"},
                    {"channelId": "1", "channelStatus": "offline"},
                ],
            },
            {"deviceId": "XYZ", "status": "offline"},
        ]
    }

    cameras = cameras_from_page(data)

    assert [(c.url, c.channel_name, c.online) for c in cameras] == [
        ("imou://ABC123/0?stream=1", "Lente fijo", True),
        ("imou://ABC123/1?stream=1", "Canal 2", False),
        ("imou://XYZ/0?stream=1", "Canal 1", False),
    ]


async def test_lists_cameras_from_the_imou_account():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("accessToken"):
            return httpx.Response(
                200,
                json={"result": {"code": "0", "data": {"accessToken": "t", "expireTime": 9999}}},
            )
        assert request.url.path.endswith("/v2/device.detail.page")
        page = {
            "deviceList": [
                {"deviceId": "ABC", "deviceName": "Cruiser", "channelList": [{"channelId": "0"}]}
            ]
        }
        return httpx.Response(200, json={"result": {"code": "0", "data": page}})

    resolver = ImouCloudResolver(
        "app", "secreto", "https://imou.example/openapi", httpx.MockTransport(handler)
    )

    cameras = await resolver.list_cameras()

    assert [camera.url for camera in cameras] == ["imou://ABC/0?stream=1"]
