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


class FrameSourceUnavailableError(Exception):
    """El equipo no puede leer video. Su mensaje es seguro: nunca incluye la URL."""


class FrameSource(Protocol):
    """Entrega JPEG de un stream. Termina o lanza una excepción si la conexión cae."""

    def stream(self, url: str) -> AsyncIterator[bytes]: ...


class UnreadableUrlError(Exception):
    """La URL se cifró con otra CAMERA_ENCRYPTION_KEY: con la clave actual no se puede leer."""


class UrlCipher(Protocol):
    def encrypt(self, url: str) -> str: ...

    def decrypt(self, encrypted: str) -> str: ...
