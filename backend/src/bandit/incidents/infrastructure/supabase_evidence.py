"""Evidencia de incidentes en Supabase Storage: visible desde cualquier backend."""

from datetime import datetime
from uuid import UUID

from bandit.shared.supabase_storage import SupabaseStorage

_FOLDER = "evidence"


class SupabaseEvidenceStore:
    def __init__(self, storage: SupabaseStorage) -> None:
        self._storage = storage

    @staticmethod
    def _path(incident_id: UUID) -> str:
        return f"{_FOLDER}/{incident_id}.jpg"

    async def save(self, incident_id: UUID, jpeg: bytes) -> None:
        await self._storage.upload(self._path(incident_id), jpeg, "image/jpeg")

    async def load(self, incident_id: UUID) -> bytes | None:
        return await self._storage.download(self._path(incident_id))

    async def purge_older_than(self, cutoff: datetime) -> int:
        old = [item.name for item in await self._storage.list(_FOLDER) if item.created_at < cutoff]
        await self._storage.delete(old)
        return len(old)
