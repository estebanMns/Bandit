"""Fotos y volantes del directorio guardados en la base de datos."""

import asyncio
from collections import OrderedDict
from datetime import UTC, datetime
from io import BytesIO
from pathlib import PurePosixPath

from PIL import Image
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
_PIL_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
# Una ficha no necesita más resolución; reducir pesos de 5 MB a unos pocos cientos de KB.
_MAX_SIDE = 640
_QUALITY = 82
_CACHE_ENTRIES = 256


def _content_type(name: str) -> str:
    suffix = PurePosixPath(name).suffix.lower()
    return _CONTENT_TYPES.get(suffix, "application/octet-stream")


def _shrink(name: str, data: bytes) -> bytes:
    """Reduce la imagen y la recodifica en su mismo formato. Si no se puede, guarda el original."""
    suffix = PurePosixPath(name).suffix.lower()
    fmt = _PIL_FORMATS.get(suffix)
    if fmt is None:
        return data
    try:
        with Image.open(BytesIO(data)) as source:
            image = source.copy()
    except (OSError, ValueError):
        return data
    image.thumbnail((_MAX_SIDE, _MAX_SIDE))
    if fmt == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    out = BytesIO()
    if fmt == "PNG":
        image.save(out, format=fmt, optimize=True)
    else:
        image.save(out, format=fmt, quality=_QUALITY, optimize=fmt == "JPEG")
    smaller = out.getvalue()
    return smaller if len(smaller) < len(data) else data


class DbMediaStore:
    """Mismo contrato que el antiguo almacén de disco, pero los bytes viajan con la base."""

    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions
        # Caché en memoria de lecturas: evita un viaje a la base por cada imagen de la página.
        # Un solo proceso del backend (ver Dockerfile); se invalida en cada escritura.
        self._cache: OrderedDict[str, StoredMedia] = OrderedDict()

    async def save(self, name: str, data: bytes) -> None:
        payload = await asyncio.to_thread(_shrink, name, data)
        row = MediaRow(
            name=name,
            content_type=_content_type(name),
            data=payload,
            updated_at=datetime.now(UTC),
        )
        async with self._sessions.begin() as session:
            await session.merge(row)
        self._cache.pop(name, None)

    async def delete(self, name: str) -> None:
        async with self._sessions.begin() as session:
            await session.execute(delete(MediaRow).where(MediaRow.name == name))
        self._cache.pop(name, None)

    async def read(self, name: str) -> StoredMedia | None:
        cached = self._cache.get(name)
        if cached is not None:
            self._cache.move_to_end(name)
            return cached
        async with self._sessions() as session:
            row = await session.get(MediaRow, name)
        if row is None:
            return None
        stored = StoredMedia(row.content_type, row.data)
        self._cache[name] = stored
        if len(self._cache) > _CACHE_ENTRIES:
            self._cache.popitem(last=False)
        return stored
