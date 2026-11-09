"""Búsqueda de cámaras en la red del local. Solo redes privadas y pequeñas."""

import ipaddress
import re
from dataclasses import dataclass, field
from enum import StrEnum

from bandit.shared.errors import InvalidDataError

# Una /24 son 256 direcciones: el tamaño de una red de casa o de un local.
_MAX_ADDRESSES = 256
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9._~\-/?=&{}%]*$")


def scan_targets(network: str) -> list[str]:
    """Direcciones a revisar. Rechaza redes públicas o más grandes que una /24."""
    try:
        parsed = ipaddress.ip_network(network.strip(), strict=False)
    except ValueError as error:
        raise InvalidDataError(
            "Escribe la red como 192.168.1.0/24 o una IP como 192.168.1.50"
        ) from error
    if parsed.version != 4 or not parsed.is_private or parsed.is_loopback:
        raise InvalidDataError("Solo se pueden revisar redes privadas, como la de tu Wi-Fi")
    if parsed.num_addresses > _MAX_ADDRESSES:
        raise InvalidDataError("La red es muy grande: usa una /24, como 192.168.1.0/24")
    hosts = list(parsed.hosts()) or [parsed.network_address]
    return [str(host) for host in hosts]


def private_host(ip: str) -> str:
    try:
        parsed = ipaddress.ip_address(ip.strip())
    except ValueError as error:
        raise InvalidDataError("La IP de la cámara no es válida") from error
    if parsed.version != 4 or not parsed.is_private or parsed.is_loopback:
        raise InvalidDataError("La cámara debe estar en una red privada")
    return str(parsed)


def safe_path(path: str) -> str | None:
    """Una ruta RTSP sin esquema, host ni credenciales. Lo demás se descarta."""
    candidate = path.strip()
    if not candidate.startswith("/"):
        candidate = "/" + candidate
    if len(candidate) > 200 or "@" in candidate or "://" in candidate:
        return None
    return candidate if _SAFE_PATH.fullmatch(candidate) else None


@dataclass(frozen=True, slots=True)
class DiscoveredDevice:
    ip: str
    open_ports: tuple[int, ...]
    brand: str | None = None
    rtsp_server: str | None = None
    http_server: str | None = None

    @property
    def has_rtsp(self) -> bool:
        return 554 in self.open_ports or 8554 in self.open_ports

    @property
    def rtsp_port(self) -> int:
        return 554 if 554 in self.open_ports else 8554


class ConnectOutcome(StrEnum):
    CONNECTED = "connected"
    WRONG_PASSWORD = "wrong_password"  # noqa: S105  Es un resultado, no una clave.
    UNREACHABLE = "unreachable"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class WorkingStream:
    path: str
    label: str
    source: str  # "conocida" o "ia"


@dataclass(slots=True)
class ConnectResult:
    outcome: ConnectOutcome
    streams: list[WorkingStream] = field(default_factory=list)
    tried: int = 0
    ai_used: bool = False
    port: int = 554
