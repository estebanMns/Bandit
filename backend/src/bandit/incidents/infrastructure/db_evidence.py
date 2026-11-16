"""Evidencia de los eventos dentro de la base de datos (Supabase).

Cualquier backend que use la misma base la ve: el PC que detectó el evento y Render. Vive mientras
exista el evento; al borrarlo, la base la borra con él (ON DELETE CASCADE).
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from bandit.incidents.infrastructure.tables import EvidenceRow
from bandit.shared.db import SessionFactory


class DbEvidenceStore:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def save(self, incident_id: UUID, jpeg: bytes) -> None:
        async with self._sessions.begin() as session:
            row = await session.get(EvidenceRow, incident_id)
            if row is None:
                row = EvidenceRow(incident_id=incident_id)
                session.add(row)
            row.jpeg = jpeg
            row.created_at = datetime.now(UTC)

    async def load(self, incident_id: UUID) -> bytes | None:
        async with self._sessions() as session:
            return await session.scalar(
                select(EvidenceRow.jpeg).where(EvidenceRow.incident_id == incident_id)
            )
