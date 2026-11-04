"""Representación pública de un incidente."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from bandit.incidents.domain.models import Incident, IncidentStatus


class AuditResponse(BaseModel):
    status: IncidentStatus
    at: datetime
    actor: str


class IncidentResponse(BaseModel):
    id: UUID
    establishment_id: UUID
    camera_id: UUID
    camera_name: str
    type: str
    severity: str
    confidence: float
    description: str
    detected_at: datetime
    status: IncidentStatus
    audit: list[AuditResponse]

    @classmethod
    def of(cls, incident: Incident) -> "IncidentResponse":
        return cls(
            id=incident.id,
            establishment_id=incident.establishment_id,
            camera_id=incident.camera_id,
            camera_name=incident.camera_name,
            type=incident.type,
            severity=incident.severity,
            confidence=incident.confidence,
            description=incident.description,
            detected_at=incident.detected_at,
            status=incident.status,
            audit=[
                AuditResponse(status=entry.status, at=entry.at, actor=entry.actor)
                for entry in incident.audit
            ],
        )
