"""Cada cliente conecta su cámara Imou con el número de serie y la clave de la etiqueta.

La cuenta de Imou de Bandit es una sola para todos los clientes. Por eso la cámara se vincula
con su propia clave (la prueba de que es de quien la conecta) y queda registrada a nombre del
local: ningún otro local puede verla ni conectarla.
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from urllib.parse import urlsplit
from uuid import UUID

from bandit.cameras.application.auto_connect import CameraCloud, CloudCamera, known_urls
from bandit.cameras.application.use_cases import ListCameras, RegisterCamera
from bandit.cameras.domain.models import IMOU_SCHEME
from bandit.cameras.domain.ports import CameraRepository, ImouOwners, UrlCipher
from bandit.shared.clock import Clock
from bandit.shared.error_summary import describe_error
from bandit.shared.errors import (
    ConflictError,
    DomainError,
    InvalidDataError,
    PermissionDeniedError,
    RateLimitedError,
    UnavailableError,
)

logger = logging.getLogger(__name__)

MAX_FAILURES = 5
FAILURE_WINDOW = timedelta(minutes=10)
_SERIAL_LENGTH = range(6, 33)


def normalize_serial(serial: str) -> str:
    """'9f0a-bc12 3456' → '9F0ABC123456'. Solo letras y números, como en la etiqueta."""
    cleaned = "".join(serial.split()).replace("-", "").upper()
    if not cleaned.isascii() or not cleaned.isalnum() or len(cleaned) not in _SERIAL_LENGTH:
        raise InvalidDataError(
            "El número de serie tiene solo letras y números (S/N en la etiqueta de la cámara)"
        )
    return cleaned


def imou_serial(url: str) -> str | None:
    """La serie de una URL imou://, o None si es otra clase de cámara."""
    parts = urlsplit(url.strip())
    return parts.netloc.upper() if parts.scheme.lower() == IMOU_SCHEME else None


@dataclass(slots=True)
class ImouConnectResult:
    added: list[str] = field(default_factory=list)
    already: int = 0


class ConnectImouCamera:
    def __init__(
        self,
        cloud: CameraCloud,
        owners: ImouOwners,
        register: RegisterCamera,
        list_cameras: ListCameras,
        cipher: UrlCipher,
        clock: Clock,
    ) -> None:
        self._cloud = cloud
        self._owners = owners
        self._register = register
        self._list = list_cameras
        self._cipher = cipher
        self._clock = clock
        self._failures: dict[UUID, deque[datetime]] = defaultdict(deque)

    async def execute(self, establishment_id: UUID, serial: str, code: str) -> ImouConnectResult:
        if not self._cloud.configured:
            raise UnavailableError("Este servidor no tiene configurada la nube de Imou")
        device_id = normalize_serial(serial)
        owner = await self._owners.owner_of(device_id)
        if owner is not None and owner != establishment_id:
            raise ConflictError("Esa cámara ya está registrada en otro local")
        self._check_attempts(establishment_id)
        try:
            await self._cloud.bind_device(device_id, code.strip())
        except DomainError:
            self._failures[establishment_id].append(self._clock.now())
            raise
        channels = await self._channels(device_id)
        await self._owners.claim(device_id, establishment_id)
        # Los canales en línea; si ninguno lo está aún, todos (se conectan cuando despierten).
        chosen = [channel for channel in channels if channel.online] or channels
        result = ImouConnectResult()
        known = await known_urls(self._list, self._cipher, establishment_id)
        for channel in chosen:
            if channel.url in known:
                result.already += 1
                continue
            name = f"{channel.device_name} · {channel.channel_name}"[:200]
            await self._register.execute(establishment_id, name, channel.url)
            known.add(channel.url)
            result.added.append(name)
        return result

    def _check_attempts(self, establishment_id: UUID) -> None:
        """Pocos intentos fallidos por local: nadie prueba claves al azar."""
        failures = self._failures[establishment_id]
        since = self._clock.now() - FAILURE_WINDOW
        while failures and failures[0] < since:
            failures.popleft()
        if len(failures) >= MAX_FAILURES:
            minutes = int(FAILURE_WINDOW.total_seconds() // 60)
            raise RateLimitedError(
                f"Demasiados intentos fallidos. Espera {minutes} minutos y revisa la etiqueta."
            )

    async def _channels(self, device_id: str) -> list[CloudCamera]:
        try:
            cameras = await self._cloud.list_cameras()
        except Exception as error:
            raise UnavailableError(f"Imou respondió: {describe_error(error)}") from error
        channels = [camera for camera in cameras if camera.device_id.upper() == device_id]
        if not channels:
            raise UnavailableError(
                "Imou vinculó la cámara pero todavía no la muestra. Intenta de nuevo en un minuto."
            )
        return channels


class ImouOwnership:
    """Una cámara imou:// solo se agrega al local que la vinculó con su clave."""

    def __init__(self, owners: ImouOwners) -> None:
        self._owners = owners

    async def ensure(self, establishment_id: UUID, url: str) -> None:
        device_id = imou_serial(url)
        if device_id is None:
            return
        owner = await self._owners.owner_of(device_id)
        if owner == establishment_id:
            return
        if owner is not None:
            raise PermissionDeniedError("Esa cámara ya está registrada en otro local")
        raise PermissionDeniedError(
            "Las cámaras Imou se conectan con su número de serie y su clave, en "
            "“Conectar cámara Imou”"
        )


class AdoptImouCameras:
    """Adjudica las cámaras imou:// ya guardadas al local que las tiene (las de antes de este
    registro), para que sigan funcionando. Si dos locales tienen la misma, la conserva el primero.
    """

    def __init__(self, cameras: CameraRepository, owners: ImouOwners, cipher: UrlCipher) -> None:
        self._cameras = cameras
        self._owners = owners
        self._cipher = cipher

    async def execute(self) -> int:
        adopted = 0
        for camera in await self._cameras.list_all():
            try:
                device_id = imou_serial(self._cipher.decrypt(camera.encrypted_url))
            except Exception as error:
                logger.warning("No se pudo leer una cámara guardada: %s", describe_error(error))
                continue
            if device_id is None or await self._owners.owner_of(device_id) is not None:
                continue
            await self._owners.claim(device_id, camera.establishment_id)
            adopted += 1
        return adopted
