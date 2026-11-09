"""Repositorio SQL del directorio."""

from sqlalchemy import select

from bandit.directory.domain.models import SyncRun, SyncTrigger, WantedRecord
from bandit.directory.infrastructure.tables import SyncRunRow, WantedRow
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


_RUN_FIELDS = (
    "started_at",
    "finished_at",
    "published",
    "rejected",
    "retired",
    "completed",
    "error",
)


class SqlSyncRunRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def save(self, run: SyncRun) -> None:
        async with self._sessions.begin() as session:
            row = await session.get(SyncRunRow, run.id)
            if row is None:
                row = SyncRunRow(id=run.id)
                session.add(row)
            row.trigger = run.trigger.value
            for name in _RUN_FIELDS:
                setattr(row, name, getattr(run, name))

    async def latest(self, limit: int) -> list[SyncRun]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(SyncRunRow).order_by(SyncRunRow.started_at.desc()).limit(limit)
            )
            return [
                SyncRun(
                    id=row.id,
                    trigger=SyncTrigger(row.trigger),
                    **{name: getattr(row, name) for name in _RUN_FIELDS},
                )
                for row in rows
            ]
