"""Fotos y volantes del directorio dentro de la base de datos (Supabase).

Así sobreviven a los despliegues y los ve cualquier backend que use la misma base, sin depender
del disco del servidor ni de configurar Supabase Storage.
"""

import re
from datetime import UTC, datetime

from sqlalchemy import delete, select

from bandit.directory.infrastructure.tables import DirectoryFileRow
from bandit.shared.db import SessionFactory

_SAFE_NAME = re.compile(r"[a-z0-9][a-z0-9._-]*")
_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def _valid(name: str) -> bool:
    # Igual que en disco: solo nombres simples, nunca rutas.
    return bool(_SAFE_NAME.fullmatch(name)) and ".." not in name and len(name) <= 320


def content_type_of(name: str) -> str:
    return _TYPES.get(name[name.rfind(".") :].lower(), "application/octet-stream")


class DbMediaStore:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def save(self, name: str, data: bytes, source: str | None = None) -> None:
        if not _valid(name):
            raise ValueError("Nombre de archivo no permitido")
        async with self._sessions.begin() as session:
            row = await session.get(DirectoryFileRow, name)
            if row is None:
                row = DirectoryFileRow(name=name)
                session.add(row)
            row.content = data
            row.content_type = content_type_of(name)
            row.source_url = source
            row.updated_at = datetime.now(UTC)

    async def delete(self, name: str) -> None:
        if not _valid(name):
            return
        async with self._sessions.begin() as session:
            await session.execute(delete(DirectoryFileRow).where(DirectoryFileRow.name == name))

    async def load(self, name: str) -> bytes | None:
        if not _valid(name):
            return None
        async with self._sessions() as session:
            return await session.scalar(
                select(DirectoryFileRow.content).where(DirectoryFileRow.name == name)
            )

    async def source_of(self, name: str) -> str | None:
        if not _valid(name):
            return None
        async with self._sessions() as session:
            return await session.scalar(
                select(DirectoryFileRow.source_url).where(DirectoryFileRow.name == name)
            )
