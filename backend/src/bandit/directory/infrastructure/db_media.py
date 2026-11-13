"""Fotos y volantes del directorio guardados en la base de datos."""

from datetime import UTC, datetime
from pathlib import PurePosixPath

from sqlalchemy import delete

from bandit.directory.domain.ports import StoredMedia
from bandit.directory.infrastructure.tables import MediaRow
from bandit.shared.db import SessionFactory

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def _content_type(name: str) -> str:
    suffix = PurePosixPath(name).suffix.lower()
    return _CONTENT_TYPES.get(suffix, "application/octet-stream")


class DbMediaStore:
    """Mismo contrato que el antiguo almacén de disco, pero los bytes viajan con la base."""

    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def save(self, name: str, data: bytes) -> None:
        row = MediaRow(
            name=name,
            content_type=_content_type(name),
            data=data,
            updated_at=datetime.now(UTC),
        )
        async with self._sessions.begin() as session:
            await session.merge(row)

    async def delete(self, name: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(delete(MediaRow).where(MediaRow.name == name))

    async def read(self, name: str) -> StoredMedia | None:
        async with self._sessions() as session:
            row = await session.get(MediaRow, name)
            return StoredMedia(row.content_type, row.data) if row else None
