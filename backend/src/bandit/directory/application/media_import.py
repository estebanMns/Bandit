"""Pasa a la base las fotos que la versión anterior dejó en disco.

Solo importa nombres que pertenecen a registros activos: una foto retirada no vuelve a aparecer
aunque su archivo siga en el disco viejo.
"""

import asyncio
from collections.abc import Iterable
from pathlib import Path

from bandit.directory.domain.ports import MediaStore


async def import_disk_media(directory: Path, store: MediaStore, referenced: Iterable[str]) -> int:
    imported = 0
    for name in sorted({item for item in referenced if item}):
        if name in {".", ".."} or "/" in name or "\\" in name:
            continue
        if await store.read(name) is not None:
            continue
        path = directory / name
        if not await asyncio.to_thread(path.is_file):
            continue
        await store.save(name, await asyncio.to_thread(path.read_bytes))
        imported += 1
    return imported
