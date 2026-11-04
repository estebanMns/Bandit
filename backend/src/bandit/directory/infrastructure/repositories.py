"""Repositorio SQL del directorio."""

from sqlalchemy import select

from bandit.directory.domain.models import WantedRecord
from bandit.directory.infrastructure.tables import WantedRow
from bandit.shared.db import SessionFactory

_COPIED_FIELDS = (
    "slug",
    "name",
    "alias",
    "crime",
    "reward",
    "region",
    "hotline_email",
    "hotline_phones",
    "photo_file",
    "flyer_file",
    "source_url",
    "first_seen_at",
    "last_seen_at",
    "active",
)


def _to_model(row: WantedRow) -> WantedRecord:
    return WantedRecord(id=row.id, **{name: getattr(row, name) for name in _COPIED_FIELDS})


class SqlWantedRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def list_active(self) -> list[WantedRecord]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(WantedRow).where(WantedRow.active).order_by(WantedRow.name)
            )
            return [_to_model(row) for row in rows]

    async def get_active(self, slug: str) -> WantedRecord | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(WantedRow).where(WantedRow.slug == slug, WantedRow.active)
            )
            return _to_model(row) if row else None

    async def upsert(self, record: WantedRecord) -> None:
        async with self._sessions.begin() as session:
            row = await session.scalar(select(WantedRow).where(WantedRow.slug == record.slug))
            if row is None:
                row = WantedRow(id=record.id)
                session.add(row)
            for name in _COPIED_FIELDS:
                setattr(row, name, getattr(record, name))
