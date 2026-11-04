"""Repositorio SQL de incidentes."""

from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, select, update

from bandit.incidents.domain.models import AuditEntry, Incident, IncidentStatus
from bandit.incidents.infrastructure.tables import AuditRow, IncidentRow
from bandit.shared.db import SessionFactory
from bandit.shared.errors import ConflictError


def _to_model(row: IncidentRow) -> Incident:
    return Incident(
        id=row.id,
        establishment_id=row.establishment_id,
        camera_id=row.camera_id,
        camera_name=row.camera_name,
        type=row.type,
        severity=row.severity,
        confidence=row.confidence,
        description=row.description,
        detected_at=row.detected_at,
        status=IncidentStatus(row.status),
        audit=[AuditEntry(IncidentStatus(a.status), a.at, a.actor) for a in row.audit],
    )


class SqlIncidentRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def add(self, incident: Incident) -> None:
        async with self._sessions.begin() as session:
            session.add(
                IncidentRow(
                    id=incident.id,
                    establishment_id=incident.establishment_id,
                    camera_id=incident.camera_id,
                    camera_name=incident.camera_name,
                    type=incident.type,
                    severity=incident.severity,
                    confidence=incident.confidence,
                    description=incident.description,
                    detected_at=incident.detected_at,
                    status=incident.status.value,
                    audit=[
                        AuditRow(
                            position=position,
                            status=entry.status.value,
                            at=entry.at,
                            actor=entry.actor,
                        )
                        for position, entry in enumerate(incident.audit)
                    ],
                )
            )

    async def save(self, incident: Incident) -> None:
        """Compara y actualiza en una sola sentencia: solo una transición simultánea gana."""
        previous = incident.audit[-2].status
        position = len(incident.audit) - 1
        async with self._sessions.begin() as session:
            result = await session.execute(
                update(IncidentRow)
                .where(IncidentRow.id == incident.id, IncidentRow.status == previous.value)
                .values(status=incident.status.value)
            )
            if cast("CursorResult[Any]", result).rowcount != 1:
                raise ConflictError("Otro operador ya actualizó este incidente")
            entry = incident.audit[-1]
            session.add(
                AuditRow(
                    incident_id=incident.id,
                    position=position,
                    status=entry.status.value,
                    at=entry.at,
                    actor=entry.actor,
                )
            )

    async def get(self, incident_id: UUID) -> Incident | None:
        async with self._sessions() as session:
            row = await session.get(IncidentRow, incident_id)
            return _to_model(row) if row else None

    async def list_recent(self, establishment_id: UUID, limit: int) -> list[Incident]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(IncidentRow)
                .where(IncidentRow.establishment_id == establishment_id)
                .order_by(IncidentRow.detected_at.desc())
                .limit(limit)
            )
            return [_to_model(row) for row in rows]
