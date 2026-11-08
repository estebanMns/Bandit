"""Evaluación de una escena: describe situaciones, nunca personas identificadas."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from bandit.shared.events import DomainEvent


class SituationType(StrEnum):
    NONE = "none"
    WEAPON = "weapon"
    ROBBERY = "robbery"
    FIGHT = "fight"
    FIRE = "fire"
    MEDICAL = "medical"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_IDENTITY_PHRASES = re.compile(
    r"\b(se llama|llamad[oa]|alias|identificad[oa] como|cuyo nombre|su nombre|"
    r"reconoc\w+ como|parece ser|podr[ií]a ser|c[eé]dula|delincuente conocido)\b",
    re.IGNORECASE,
)
# Dos palabras capitalizadas seguidas después del inicio de la frase suelen ser un nombre propio.
_PROPER_NAME = re.compile(r"(?<![.!?]\s)(?<!^)\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b")


def mentions_identity(text: str) -> bool:
    return bool(_IDENTITY_PHRASES.search(text) or _PROPER_NAME.search(text))


@dataclass(frozen=True, slots=True)
class SceneAssessment:
    type: SituationType
    severity: Severity
    confidence: float
    description: str

    @classmethod
    def calm(cls) -> "SceneAssessment":
        return cls(SituationType.NONE, Severity.LOW, 1.0, "")


class ActivityOutcome(StrEnum):
    """Qué pasó con un fotograma muestreado."""

    ANALYZED = "analyzed"
    NO_MOTION = "no_motion"
    OVER_BUDGET = "over_budget"
    ERROR = "error"
    FILTERED = "filtered"


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalysisActivity(DomainEvent):
    """Rastro de cada muestreo, para mostrar en vivo lo que hace el modelo."""

    camera_id: UUID
    establishment_id: UUID
    camera_name: str
    at: datetime
    outcome: ActivityOutcome
    motion: float
    assessment: SceneAssessment | None
    streak: int
    streak_target: int
    alerted: bool
    # Solo en memoria: nunca se guarda en disco ni viaja por el WebSocket.
    jpeg: bytes | None


@dataclass(frozen=True, slots=True, kw_only=True)
class SituationDetected(DomainEvent):
    camera_id: UUID
    establishment_id: UUID
    camera_name: str
    assessment: SceneAssessment
    evidence_jpeg: bytes
    detected_at: datetime
