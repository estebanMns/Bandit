"""Fotos y volantes del directorio en Supabase Storage: sobreviven a los despliegues."""

import re

from bandit.shared.supabase_storage import SupabaseStorage

_FOLDER = "directory"
_SAFE_NAME = re.compile(r"[a-z0-9][a-z0-9._-]*")
_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def _path(name: str) -> str:
    # Igual que en disco: solo nombres simples, nunca rutas.
    if not _SAFE_NAME.fullmatch(name) or ".." in name:
        raise ValueError("Nombre de archivo no permitido")
    return f"{_FOLDER}/{name}"


class SupabaseMediaStore:
    def __init__(self, storage: SupabaseStorage) -> None:
        self._storage = storage

    async def save(self, name: str, data: bytes) -> None:
        content_type = _TYPES.get(name[name.rfind(".") :].lower(), "application/octet-stream")
        await self._storage.upload(_path(name), data, content_type)

    async def delete(self, name: str) -> None:
        await self._storage.delete([_path(name)])

    async def load(self, name: str) -> bytes | None:
        try:
            path = _path(name)
        except ValueError:
            return None
        return await self._storage.download(path)
