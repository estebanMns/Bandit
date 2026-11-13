"""Conectar las cámaras del local por el medio que funcione: red local o nube de Imou."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol
from urllib.parse import quote
from uuid import UUID

from bandit.cameras.application.discovery import ConnectDevice, ScanNetwork
from bandit.cameras.application.use_cases import ListCameras, RegisterCamera
from bandit.cameras.domain.discovery import ConnectOutcome, DiscoveredDevice
from bandit.cameras.domain.ports import UrlCipher
from bandit.shared.error_summary import describe_error
from bandit.shared.errors import DomainError

logger = logging.getLogger(__name__)

_RTSP_PORTS = {554, 8554}


class CloudCamera(Protocol):
    @property
    def url(self) -> str: ...

    @property
    def device_name(self) -> str: ...

    @property
    def channel_name(self) -> str: ...

    @property
    def online(self) -> bool: ...


class CameraCloud(Protocol):
    """Una nube de cámaras que puede listar las de la cuenta (hoy, Imou)."""

    @property
    def configured(self) -> bool: ...

    async def list_cameras(self) -> Sequence[CloudCamera]: ...


class Method(StrEnum):
    LAN = "red_local"
    CLOUD = "nube_imou"


class AttemptStatus(StrEnum):
    CONNECTED = "conectada"
    NOTHING_FOUND = "sin_camaras"
    BLOCKED = "bloqueada"
    WRONG_PASSWORD = "clave_incorrecta"  # noqa: S105  Es un estado, no una clave.
    NEEDS_PASSWORD = "falta_clave"  # noqa: S105  Es un estado, no una clave.
    NOT_CONFIGURED = "sin_configurar"
    SKIPPED = "omitido"
    FAILED = "error"


@dataclass(frozen=True, slots=True)
class Attempt:
    method: Method
    status: AttemptStatus
    detail: str


@dataclass(slots=True)
class AutoConnectResult:
    attempts: list[Attempt] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    already: int = 0

    @property
    def connected(self) -> bool:
        return bool(self.added) or self.already > 0


class AutoConnect:
    """Primero la red local; si no alcanza, la nube de Imou. Cada intento queda reportado."""

    def __init__(
        self,
        scan: ScanNetwork,
        connect: ConnectDevice,
        register: RegisterCamera,
        list_cameras: ListCameras,
        cipher: UrlCipher,
        cloud: CameraCloud,
    ) -> None:
        self._scan = scan
        self._connect = connect
        self._register = register
        self._list = list_cameras
        self._cipher = cipher
        self._cloud = cloud

    async def execute(
        self, establishment_id: UUID, network: str | None, username: str, password: str
    ) -> AutoConnectResult:
        result = AutoConnectResult()
        known = await self._known_urls(establishment_id)
        await self._try_lan(establishment_id, network, username, password, known, result)
        if not result.connected:
            await self._try_cloud(establishment_id, known, result)
        else:
            result.attempts.append(
                Attempt(
                    Method.CLOUD, AttemptStatus.SKIPPED, "No hizo falta: la red local funcionó."
                )
            )
        return result

    async def _known_urls(self, establishment_id: UUID) -> set[str]:
        urls: set[str] = set()
        for camera in await self._list.execute(establishment_id):
            try:
                urls.add(self._cipher.decrypt(camera.encrypted_url))
            except Exception as error:
                logger.warning("No se pudo leer una cámara guardada: %s", describe_error(error))
        return urls

    async def _try_lan(
        self,
        establishment_id: UUID,
        network: str | None,
        username: str,
        password: str,
        known: set[str],
        result: AutoConnectResult,
    ) -> None:
        if not network:
            result.attempts.append(
                Attempt(Method.LAN, AttemptStatus.SKIPPED, "No se indicó la red del Wi-Fi.")
            )
            return
        try:
            devices = await self._scan.execute(establishment_id, network)
        except DomainError as error:
            result.attempts.append(Attempt(Method.LAN, AttemptStatus.FAILED, str(error)))
            return
        cameras = [device for device in devices if set(device.open_ports) & _RTSP_PORTS]
        if not cameras:
            answered = (
                "respondió 1 equipo"
                if len(devices) == 1
                else f"respondieron {len(devices)} equipos"
            )
            result.attempts.append(
                Attempt(
                    Method.LAN,
                    AttemptStatus.NOTHING_FOUND,
                    f"Se revisó la red y {answered}, ninguno con video RTSP. "
                    "Si la cámara está en este Wi-Fi, puede estar bloqueando a este equipo.",
                )
            )
            return
        if not password:
            names = ", ".join(device.ip for device in cameras)
            result.attempts.append(
                Attempt(
                    Method.LAN,
                    AttemptStatus.NEEDS_PASSWORD,
                    f"Se encontraron cámaras en {names}. Escribe su clave para conectarlas.",
                )
            )
            return
        await self._connect_lan(establishment_id, cameras, username, password, known, result)

    async def _connect_lan(
        self,
        establishment_id: UUID,
        cameras: list[DiscoveredDevice],
        username: str,
        password: str,
        known: set[str],
        result: AutoConnectResult,
    ) -> None:
        statuses: list[AttemptStatus] = []
        for device in cameras:
            outcome = await self._connect.execute(device.ip, username, password)
            if outcome.outcome is ConnectOutcome.WRONG_PASSWORD:
                statuses.append(AttemptStatus.WRONG_PASSWORD)
                continue
            if outcome.outcome is not ConnectOutcome.CONNECTED:
                statuses.append(AttemptStatus.BLOCKED)
                continue
            for stream in outcome.streams:
                url = _rtsp_url(device.ip, outcome.port, stream.path, username, password)
                await self._add(
                    establishment_id,
                    f"{device.brand or 'Cámara'} {stream.label}",
                    url,
                    known,
                    result,
                )
        if result.connected:
            result.attempts.append(
                Attempt(Method.LAN, AttemptStatus.CONNECTED, "Conectada por la red local.")
            )
        elif AttemptStatus.WRONG_PASSWORD in statuses:
            result.attempts.append(
                Attempt(
                    Method.LAN,
                    AttemptStatus.WRONG_PASSWORD,
                    "La cámara rechazó la clave. No se reintentó para que la cámara no bloquee "
                    "a este equipo: revisa la clave o el código de la etiqueta.",
                )
            )
        else:
            result.attempts.append(
                Attempt(
                    Method.LAN,
                    AttemptStatus.BLOCKED,
                    "La cámara aparece en la red pero no entrega video a este equipo.",
                )
            )

    async def _try_cloud(
        self, establishment_id: UUID, known: set[str], result: AutoConnectResult
    ) -> None:
        if not self._cloud.configured:
            result.attempts.append(
                Attempt(
                    Method.CLOUD,
                    AttemptStatus.NOT_CONFIGURED,
                    "Falta configurar la nube de Imou: IMOU_APP_ID e IMOU_APP_SECRET.",
                )
            )
            return
        try:
            cameras = await self._cloud.list_cameras()
        except Exception as error:
            result.attempts.append(
                Attempt(
                    Method.CLOUD, AttemptStatus.FAILED, f"Imou respondió: {describe_error(error)}"
                )
            )
            return
        online = [camera for camera in cameras if camera.online]
        if not online:
            result.attempts.append(
                Attempt(
                    Method.CLOUD,
                    AttemptStatus.NOTHING_FOUND,
                    f"La cuenta de Imou tiene {len(cameras)} canales y ninguno está en línea.",
                )
            )
            return
        for camera in online:
            name = f"{camera.device_name} · {camera.channel_name}"
            await self._add(establishment_id, name, camera.url, known, result)
        result.attempts.append(
            Attempt(Method.CLOUD, AttemptStatus.CONNECTED, "Conectada por la nube de Imou.")
        )

    async def _add(
        self,
        establishment_id: UUID,
        name: str,
        url: str,
        known: set[str],
        result: AutoConnectResult,
    ) -> None:
        if url in known:
            result.already += 1
            return
        await self._register.execute(establishment_id, name[:200], url)
        known.add(url)
        result.added.append(name)


def _rtsp_url(ip: str, port: int, path: str, username: str, password: str) -> str:
    credentials = f"{quote(username, safe='')}:{quote(password, safe='')}"
    return f"rtsp://{credentials}@{ip}:{port}{path}"
