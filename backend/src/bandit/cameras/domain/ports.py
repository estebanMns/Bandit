"""Puertos del módulo de cámaras."""

from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from bandit.cameras.domain.models import Camera


class CameraRepository(Protocol):
    async def add(self, camera: Camera) -> None: ...

    async def save(self, camera: Camera) -> None: ...

    async def get(self, camera_id: UUID) -> Camera | None: ...

    async def delete(self, camera_id: UUID) -> None: ...

    async def list_for(self, establishment_id: UUID) -> list[Camera]: ...

    async def list_enabled(self) -> list[Camera]: ...


PRIVATE_NETWORK = "private_network"


class FrameSourceUnavailableError(Exception):
    """El equipo no puede leer video. Su mensaje es seguro: nunca incluye la URL.

    `kind` dice qué tipo de problema es, para que la app ofrezca la salida adecuada; por
    ejemplo PRIVATE_NETWORK: la cámara está en una red que este servidor no alcanza.
    """

    def __init__(self, message: str, kind: str | None = None) -> None:
        super().__init__(message)
        self.kind = kind


class FrameSource(Protocol):
    """Entrega JPEG de un stream. Termina o lanza una excepción si la conexión cae."""

    def stream(self, url: str) -> AsyncIterator[bytes]: ...


class UnreadableUrlError(Exception):
    """La URL se cifró con otra CAMERA_ENCRYPTION_KEY: con la clave actual no se puede leer."""


class UrlCipher(Protocol):
    def encrypt(self, url: str) -> str: ...

    def decrypt(self, encrypted: str) -> str: ...
