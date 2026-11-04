"""Agregado Incidente: la confirmación humana es parte de sus reglas."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from bandit.shared.errors import ConflictError
from bandit.shared.events import DomainEvent


class IncidentStatus(StrEnum):
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    DISCARDED = "discarded"
    NOTIFIED = "notified"
    NOTIFICATION_FAILED = "notification_failed"


_ALLOWED_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    IncidentStatus.DETECTED: frozenset({IncidentStatus.CONFIRMED, IncidentStatus.DISCARDED}),
    IncidentStatus.CONFIRMED: frozenset(
        {IncidentStatus.NOTIFIED, IncidentStatus.NOTIFICATION_FAILED}
    ),
    IncidentStatus.NOTIFICATION_FAILED: frozenset({IncidentStatus.CONFIRMED}),
    IncidentStatus.DISCARDED: frozenset(),
    IncidentStatus.NOTIFIED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class AuditEntry:
    status: IncidentStatus
    at: datetime
    actor: str
    """Correo del operador, o `sistema` si la transición es automática."""


@dataclass(slots=True)
class Incident:
    id: UUID
    establishment_id: UUID
    camera_id: UUID
    camera_name: str
    type: str
    severity: str
    confidence: float
    description: str
    detected_at: datetime
    status: IncidentStatus = IncidentStatus.DETECTED
    audit: list[AuditEntry] = field(default_factory=list)
    previous_status: IncidentStatus | None = None
    """Estado desde el que partió la última transición en memoria; protege el guardado."""

    def __post_init__(self) -> None:
        if not self.audit:
            self.audit.append(AuditEntry(self.status, self.detected_at, "sistema"))

    def _transition(self, target: IncidentStatus, at: datetime, actor: str) -> None:
        if target not in _ALLOWED_TRANSITIONS[self.status]:
            raise ConflictError(f"El incidente ya está en estado {self.status.value}")
        self.previous_status = self.status
        self.status = target
        self.audit.append(AuditEntry(target, at, actor))

    def confirm(self, at: datetime, actor: str) -> None:
        self._transition(IncidentStatus.CONFIRMED, at, actor)

    def discard(self, at: datetime, actor: str) -> None:
        self._transition(IncidentStatus.DISCARDED, at, actor)

    def mark_notified(self, at: datetime) -> None:
        self._transition(IncidentStatus.NOTIFIED, at, "sistema")

    def mark_notification_failed(self, at: datetime) -> None:
        self._transition(IncidentStatus.NOTIFICATION_FAILED, at, "sistema")


@dataclass(frozen=True, slots=True, kw_only=True)
class IncidentChanged(DomainEvent):
    """Cualquier cambio de estado; lo consumen quienes solo informan."""

    incident: Incident


@dataclass(frozen=True, slots=True, kw_only=True)
class IncidentConfirmed(DomainEvent):
    """Único evento que autoriza a enviar una alerta externa."""

    incident: Incident
    confirmed_by: str
