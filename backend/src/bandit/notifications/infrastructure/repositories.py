"""Repositorio SQL de suscripciones Web Push."""

from uuid import UUID

from sqlalchemy import delete, select

from bandit.notifications.domain.models import PushTarget
from bandit.notifications.infrastructure.tables import PushTargetRow
from bandit.shared.db import SessionFactory


class SqlPushTargetRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def add(self, establishment_id: UUID, target: PushTarget) -> None:
        async with self._sessions.begin() as session:
            await session.merge(
                PushTargetRow(
                    endpoint=target.endpoint,
                    establishment_id=establishment_id,
                    p256dh=target.p256dh,
                    auth=target.auth,
                )
            )

    async def list_for(self, establishment_id: UUID) -> list[PushTarget]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(PushTargetRow).where(PushTargetRow.establishment_id == establishment_id)
            )
            return [PushTarget(row.endpoint, row.p256dh, row.auth) for row in rows]

    async def remove(self, endpoint: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(delete(PushTargetRow).where(PushTargetRow.endpoint == endpoint))
