"""Candidatos del boletín: la foto publicada de cada registro activo, con caché corta."""

import time
from collections.abc import Awaitable, Callable

from bandit.faces.domain.models import WatchedPerson

_CACHE_SECONDS = 30

LoadPeople = Callable[[], Awaitable[list[WatchedPerson]]]


class BulletinWatchList:
    def __init__(self, load: LoadPeople) -> None:
        self._load = load
        self._cached: list[WatchedPerson] = []
        self._cached_at = float("-inf")

    async def people(self) -> list[WatchedPerson]:
        if time.monotonic() - self._cached_at < _CACHE_SECONDS:
            return self._cached
        self._cached = await self._load()
        self._cached_at = time.monotonic()
        return self._cached
