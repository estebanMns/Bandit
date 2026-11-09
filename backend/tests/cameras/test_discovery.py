"""Buscar y conectar cámaras: solo redes privadas, la clave nunca llega a la IA."""

from datetime import timedelta
from uuid import uuid4

import pytest

from bandit.cameras.application.discovery import ConnectDevice, ScanNetwork
from bandit.cameras.domain.discovery import (
    ConnectOutcome,
    DiscoveredDevice,
    safe_path,
    scan_targets,
)
from bandit.cameras.infrastructure.lan_scanner import guess_brand
from bandit.shared.errors import InvalidDataError, RateLimitedError

IMOU = DiscoveredDevice("192.168.1.102", (554, 37777), "Dahua / Imou", "Rtsp Server/3.0")
UNKNOWN = DiscoveredDevice("192.168.1.50", (554,), None, "Mystery/1.0")
GOOD = "buena"


class FakeScanner:
    def __init__(self, device=None):
        self.device = device
        self.scanned: list[str] = []

    async def scan(self, hosts):
        self.scanned = list(hosts)
        return [UNKNOWN, IMOU, DiscoveredDevice("192.168.1.1", (80,), None, None, "Router")]

    async def inspect(self, ip):
        return self.device


class FakeProber:
    """Responde 200 solo a las rutas indicadas; 401 a todo si la clave es mala."""

    def __init__(self, good_paths=()):
        self.good_paths = set(good_paths)
        self.password = GOOD
        self.paths: list[str] = []

    async def describe(self, ip, port, path, username, password):
        self.paths.append(path)
        if password != self.password:
            return 401
        return 200 if path in self.good_paths else 404


class FakeAdvisor:
    def __init__(self, paths):
        self.paths = paths
        self.devices: list[DiscoveredDevice] = []

    async def suggest(self, device):
        self.devices.append(device)
        return self.paths


@pytest.mark.parametrize("network", ["8.8.8.0/24", "127.0.0.1", "10.0.0.0/16", "no-es-red"])
def test_rejects_public_huge_or_invalid_networks(network):
    with pytest.raises(InvalidDataError):
        scan_targets(network)


def test_accepts_a_home_network_and_a_single_ip():
    assert len(scan_targets("192.168.1.0/24")) == 254
    assert scan_targets("192.168.1.50") == ["192.168.1.50"]


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("cam/realmonitor?channel=1&subtype=1", "/cam/realmonitor?channel=1&subtype=1"),
        ("/stream2", "/stream2"),
        ("rtsp://evil.example/x", None),
        ("/x@evil", None),
        ("/con espacios", None),
    ],
)
def test_only_plain_paths_are_tried(path, expected):
    assert safe_path(path) == expected


def test_guesses_brand_from_headers():
    assert guess_brand("Dahua Rtsp Server", None) == "Dahua / Imou"
    assert guess_brand(None, "App-webs/") == "Hikvision / EZVIZ"
    assert guess_brand(None, "nginx") is None


async def test_cameras_come_first_and_scans_are_spaced(clock):
    scanner = FakeScanner()
    scan = ScanNetwork(scanner, clock, timedelta(minutes=2))
    local = uuid4()

    devices = await scan.execute(local, "192.168.1.0/24")

    assert [device.ip for device in devices] == ["192.168.1.102", "192.168.1.50", "192.168.1.1"]
    with pytest.raises(RateLimitedError):
        await scan.execute(local, "192.168.1.0/24")
    clock.advance(minutes=3)
    await scan.execute(local, "192.168.1.0/24")


async def test_connects_both_lenses_with_known_paths():
    good = {"/cam/realmonitor?channel=1&subtype=1", "/cam/realmonitor?channel=2&subtype=1"}
    advisor = FakeAdvisor(["/nunca"])
    connect = ConnectDevice(FakeScanner(IMOU), FakeProber(good), advisor)

    result = await connect.execute("192.168.1.102", "admin", "buena")

    assert result.outcome is ConnectOutcome.CONNECTED
    assert [stream.label for stream in result.streams] == ["Lente 1", "Lente 2"]
    assert advisor.devices == []


async def test_wrong_password_is_reported_without_asking_the_ai():
    advisor = FakeAdvisor(["/otra"])
    connect = ConnectDevice(FakeScanner(IMOU), FakeProber(), advisor)

    result = await connect.execute("192.168.1.102", "admin", "mala")

    assert result.outcome is ConnectOutcome.WRONG_PASSWORD
    assert advisor.devices == []


async def test_ai_suggests_paths_when_known_ones_fail_and_never_sees_the_password():
    advisor = FakeAdvisor(["/live/main", "rtsp://evil/x", "/video{channel}"])
    prober = FakeProber({"/video2"})
    connect = ConnectDevice(FakeScanner(UNKNOWN), prober, advisor)

    result = await connect.execute("192.168.1.50", "admin", "buena")

    assert result.outcome is ConnectOutcome.CONNECTED and result.ai_used
    assert [(s.path, s.source) for s in result.streams] == [("/video2", "ia")]
    assert "buena" not in repr(advisor.devices)
    assert all("evil" not in path for path in prober.paths)


async def test_unreachable_device_is_reported():
    connect = ConnectDevice(FakeScanner(None), FakeProber(), FakeAdvisor([]))

    result = await connect.execute("192.168.1.102", "admin", "buena")

    assert result.outcome is ConnectOutcome.UNREACHABLE
