"""Cámara y fotograma."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlsplit
from uuid import UUID

from bandit.shared.errors import InvalidDataError
from bandit.shared.events import DomainEvent

_ALLOWED_SCHEMES = {"rtsp", "rtsps"}


class CameraStatus(StrEnum):
    STOPPED = "stopped"
    CONNECTING = "connecting"
    LIVE = "live"
    RETRYING = "retrying"


def validate_stream_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if parts.scheme.lower() not in _ALLOWED_SCHEMES or not parts.hostname:
        raise InvalidDataError("La URL debe empezar por rtsp:// o rtsps:// e incluir un host")
    return url.strip()


@dataclass(slots=True)
class Camera:
    id: UUID
    establishment_id: UUID
    name: str
    encrypted_url: str
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidDataError("La cámara necesita un nombre")


@dataclass(frozen=True, slots=True)
class Frame:
    camera_id: UUID
    jpeg: bytes
    captured_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CameraStatusChanged(DomainEvent):
    camera_id: UUID
    establishment_id: UUID
    status: CameraStatus
