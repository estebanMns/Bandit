"""Prueba de rostros: compara a quien aparece en cámara con registros de prueba consentidos."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from bandit.shared.clock import Clock
from bandit.shared.events import DomainEvent

MATCH_THRESHOLD = 0.8


class FaceOutcome(StrEnum):
    MATCH = "match"
    NO_MATCH = "no_match"
    NO_FACE = "no_face"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class WatchedPerson:
    """Persona de prueba que dio su consentimiento, con sus fotos de referencia."""

    name: str
    references: tuple[bytes, ...]


@dataclass(frozen=True, slots=True)
class FaceVerdict:
    face_visible: bool
    same_person: bool
    confidence: float
    explanation: str

    @property
    def confident_match(self) -> bool:
        return self.face_visible and self.same_person and self.confidence >= MATCH_THRESHOLD


@dataclass(frozen=True, slots=True)
class FaceCheck:
    id: UUID
    camera_id: UUID
    camera_name: str
    establishment_id: UUID
    at: datetime
    outcome: FaceOutcome
    person: str | None
    confidence: float
    explanation: str
    alerted: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class FaceCheckDone(DomainEvent):
    check: FaceCheck
    # Solo en memoria: nunca viaja por el WebSocket.
    jpeg: bytes


class DailyLimit:
    """Tope diario de consultas de la prueba de rostros."""

    def __init__(self, limit: int, clock: Clock) -> None:
        self.limit = limit
        self._clock = clock
        self._day: date | None = None
        self._used = 0

    @property
    def used(self) -> int:
        self._roll()
        return self._used

    def _roll(self) -> None:
        today = self._clock.now().date()
        if today != self._day:
            self._day, self._used = today, 0

    def try_spend(self) -> bool:
        self._roll()
        if self._used >= self.limit:
            return False
        self._used += 1
        return True
