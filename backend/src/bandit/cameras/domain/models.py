"""Cámara y fotograma."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from bandit.shared.errors import InvalidDataError
from bandit.shared.events import DomainEvent

_RTSP_SCHEMES = {"rtsp", "rtsps"}
IMOU_SCHEME = "imou"


class CameraStatus(StrEnum):
    STOPPED = "stopped"
    CONNECTING = "connecting"
    LIVE = "live"
    RETRYING = "retrying"


def validate_stream_url(url: str) -> str:
    """Acepta RTSP directo o una cámara Imou por su nube: imou://<serie>/<canal>?stream=0|1."""
    cleaned = url.strip()
    parts = urlsplit(cleaned)
    scheme = parts.scheme.lower()
    if scheme in _RTSP_SCHEMES and parts.hostname:
        return cleaned
    if scheme == IMOU_SCHEME:
        channel = parts.path.strip("/")
        stream = parse_qs(parts.query).get("stream", ["1"])[0]
        if parts.netloc.isalnum() and channel.isdigit() and stream in {"0", "1"}:
            return cleaned
        raise InvalidDataError(
            "Para Imou usa imou://<número de serie>/<canal>?stream=1 (1 ligera, 0 alta)"
        )
    raise InvalidDataError("La URL debe empezar por rtsp://, rtsps:// o imou://")


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
