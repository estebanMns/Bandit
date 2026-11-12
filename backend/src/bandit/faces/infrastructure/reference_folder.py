"""Fotos de referencia en disco: <raíz>/<slug>/*.jpg, una carpeta por persona de prueba."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from bandit.faces.domain.models import WatchedPerson

MAX_REFERENCES = 3
_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_CACHE_SECONDS = 30

# Devuelve (nombre, slug) de cada persona de prueba con consentimiento.
PeopleSource = Callable[[], Awaitable[list[tuple[str, str]]]]


class ReferenceFolderWatchList:
    def __init__(self, root: str, source: PeopleSource) -> None:
        self._root = Path(root)
        self._source = source
        self._cached: list[WatchedPerson] = []
        self._cached_at = float("-inf")

    async def people(self) -> list[WatchedPerson]:
        if time.monotonic() - self._cached_at < _CACHE_SECONDS:
            return self._cached
        names = await self._source()
        loaded = await asyncio.to_thread(self._load, names)
        self._cached, self._cached_at = loaded, time.monotonic()
        return loaded

    def _load(self, names: list[tuple[str, str]]) -> list[WatchedPerson]:
        people = []
        for name, slug in names:
            folder = self._root / slug
            if not folder.is_dir() or folder.parent != self._root:
                continue
            files = sorted(p for p in folder.iterdir() if p.suffix.lower() in _EXTENSIONS)
            references = tuple(path.read_bytes() for path in files[:MAX_REFERENCES])
            if references:
                people.append(WatchedPerson(name, references))
        return people
