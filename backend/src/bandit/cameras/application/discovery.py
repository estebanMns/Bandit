"""Casos de uso para encontrar y conectar cámaras de la red del local."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from bandit.cameras.domain.discovery import (
    ConnectOutcome,
    ConnectResult,
    DiscoveredDevice,
    WorkingStream,
    private_host,
    safe_path,
    scan_targets,
)
from bandit.shared.clock import Clock
from bandit.shared.error_summary import describe_error
from bandit.shared.errors import RateLimitedError

logger = logging.getLogger(__name__)

OK, UNAUTHORIZED = 200, 401
_MAX_AI_PATHS = 8


class NetworkScanner(Protocol):
    async def scan(self, hosts: Sequence[str]) -> list[DiscoveredDevice]: ...

    async def inspect(self, ip: str) -> DiscoveredDevice | None: ...


class RtspProber(Protocol):
    async def describe(self, ip: str, port: int, path: str, username: str, password: str) -> int:
        """Código RTSP de DESCRIBE (200, 404...), 401 si rechazó la clave o 0 sin respuesta."""
        ...


class PathAdvisor(Protocol):
    async def suggest(self, device: DiscoveredDevice) -> list[str]:
        """Rutas RTSP probables. Nunca recibe la clave de la cámara."""
        ...


@dataclass(frozen=True, slots=True)
class _Template:
    path: str
    label: str


# Rutas públicas y documentadas por fabricante; {channel} se reemplaza por 1, 2...
_KNOWN: dict[str | None, tuple[_Template, ...]] = {
    "Dahua / Imou": (_Template("/cam/realmonitor?channel={channel}&subtype=1", "Lente {channel}"),),
    "Hikvision / EZVIZ": (_Template("/Streaming/Channels/{channel}02", "Canal {channel}"),),
    "TP-Link Tapo": (_Template("/stream2", "Calidad ligera"),),
    "Reolink": (_Template("/h264Preview_0{channel}_sub", "Canal {channel}"),),
}
_GENERIC = (
    _Template("/cam/realmonitor?channel={channel}&subtype=1", "Lente {channel}"),
    _Template("/Streaming/Channels/{channel}02", "Canal {channel}"),
    _Template("/stream2", "Calidad ligera"),
    _Template("/live/ch0{channel}_1", "Canal {channel}"),
    _Template("/onvif1", "ONVIF"),
    _Template("/h264", "H.264"),
)
_CHANNELS = (1, 2)


def _expand(templates: Sequence[_Template]) -> list[_Template]:
    expanded: dict[str, _Template] = {}
    for template in templates:
        channels = _CHANNELS if "{channel}" in template.path else (1,)
        for channel in channels:
            path = template.path.replace("{channel}", str(channel))
            expanded.setdefault(
                path, _Template(path, template.label.replace("{channel}", str(channel)))
            )
    return list(expanded.values())


class ScanNetwork:
    """Una búsqueda cada pocos minutos por local: barrer la red no debe volverse ruido."""

    def __init__(self, scanner: NetworkScanner, clock: Clock, gap: timedelta) -> None:
        self._scanner = scanner
        self._clock = clock
        self._gap = gap
        self._last: dict[UUID, datetime] = {}

    async def execute(self, establishment_id: UUID, network: str) -> list[DiscoveredDevice]:
        hosts = scan_targets(network)
        now = self._clock.now()
        last = self._last.get(establishment_id)
        if last is not None and now - last < self._gap:
            seconds = int((self._gap - (now - last)).total_seconds()) + 1
            raise RateLimitedError(f"Espera {seconds} segundos antes de buscar de nuevo")
        self._last[establishment_id] = now
        devices = await self._scanner.scan(hosts)
        # Primero lo que habla RTSP: es lo que más probablemente es una cámara.
        return sorted(devices, key=lambda device: (not device.has_rtsp, device.ip))


class ConnectDevice:
    """Prueba rutas conocidas; si ninguna responde, le pide a la IA otras para probar."""

    def __init__(self, scanner: NetworkScanner, prober: RtspProber, advisor: PathAdvisor) -> None:
        self._scanner = scanner
        self._prober = prober
        self._advisor = advisor

    async def execute(self, ip: str, username: str, password: str) -> ConnectResult:
        device = await self._scanner.inspect(private_host(ip))
        if device is None or not device.has_rtsp:
            return ConnectResult(ConnectOutcome.UNREACHABLE)

        known = _expand(_KNOWN.get(device.brand) or _GENERIC)
        result = await self._try(device, known, username, password, source="conocida")
        if result.outcome is ConnectOutcome.NOT_FOUND:
            suggested = await self._ask_ai(device, {template.path for template in known})
            if suggested:
                ai = await self._try(device, suggested, username, password, source="ia")
                ai.tried += result.tried
                ai.ai_used = True
                return ai
        return result

    async def _ask_ai(self, device: DiscoveredDevice, already: set[str]) -> list[_Template]:
        try:
            proposals = await self._advisor.suggest(device)
        except Exception as error:
            logger.warning("La IA no pudo proponer rutas: %s", describe_error(error))
            return []
        cleaned = [safe_path(path) for path in proposals]
        templates = [_Template(path, "Sugerida por la IA") for path in cleaned if path]
        return [t for t in _expand(templates) if t.path not in already][:_MAX_AI_PATHS]

    async def _try(
        self,
        device: DiscoveredDevice,
        templates: Sequence[_Template],
        username: str,
        password: str,
        source: str,
    ) -> ConnectResult:
        result = ConnectResult(ConnectOutcome.NOT_FOUND, port=device.rtsp_port)
        for template in templates:
            result.tried += 1
            status = await self._prober.describe(
                device.ip, device.rtsp_port, template.path, username, password
            )
            if status == UNAUTHORIZED:
                # Cada clave rechazada cuenta como inicio de sesión fallido: tras unos pocos,
                # la cámara bloquea a este equipo. Se para al primero.
                if not result.streams:
                    result.outcome = ConnectOutcome.WRONG_PASSWORD
                    return result
                break
            if status == OK:
                result.streams.append(WorkingStream(template.path, template.label, source))
        if result.streams:
            result.outcome = ConnectOutcome.CONNECTED
        return result
