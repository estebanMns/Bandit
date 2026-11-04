"""Archivos publicados del directorio."""

import asyncio
from pathlib import Path


class FileMediaStore:
    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def _safe_path(self, name: str) -> Path:
        path = (self._root / name).resolve()
        if path.parent != self._root:
            raise ValueError("Nombre de archivo no permitido")
        return path

    def _write(self, name: str, data: bytes) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        self._safe_path(name).write_bytes(data)

    async def save(self, name: str, data: bytes) -> None:
        await asyncio.to_thread(self._write, name, data)

    async def delete(self, name: str) -> None:
        await asyncio.to_thread(self._safe_path(name).unlink, missing_ok=True)

    def path_of(self, name: str) -> str | None:
        try:
            path = self._safe_path(name)
        except ValueError:
            return None
        return str(path) if path.is_file() else None
