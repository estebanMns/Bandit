"""Evidencia en disco. Solo fotogramas de incidentes, con retención limitada."""

import asyncio
from datetime import datetime
from pathlib import Path
from uuid import UUID


class FileEvidenceStore:
    def __init__(self, root: str) -> None:
        self._root = Path(root)

    def _path(self, incident_id: UUID) -> Path:
        return self._root / f"{incident_id}.jpg"

    def _write(self, incident_id: UUID, jpeg: bytes) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        self._path(incident_id).write_bytes(jpeg)

    async def save(self, incident_id: UUID, jpeg: bytes) -> None:
        await asyncio.to_thread(self._write, incident_id, jpeg)

    def _read(self, incident_id: UUID) -> bytes | None:
        path = self._path(incident_id)
        return path.read_bytes() if path.exists() else None

    async def load(self, incident_id: UUID) -> bytes | None:
        return await asyncio.to_thread(self._read, incident_id)

    def _purge(self, cutoff: datetime) -> int:
        if not self._root.exists():
            return 0
        removed = 0
        for path in self._root.glob("*.jpg"):
            if path.stat().st_mtime < cutoff.timestamp():
                path.unlink(missing_ok=True)
                removed += 1
        return removed

    async def purge_older_than(self, cutoff: datetime) -> int:
        return await asyncio.to_thread(self._purge, cutoff)
