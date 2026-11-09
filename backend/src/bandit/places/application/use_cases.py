"""CAI cercanos al local y mosaicos del mapa, con caché."""

import time

from bandit.places.domain.models import Place, require_service_area, tile_allowed
from bandit.places.domain.ports import PoliceStations, TileSource
from bandit.shared.errors import InvalidDataError, NotFoundError

_CACHE_SECONDS = 24 * 3600
_MAX_RADIUS_M = 10_000


class FindNearbyCai:
    """Los CAI más cercanos primero. La consulta se guarda un día por zona."""

    def __init__(self, stations: PoliceStations) -> None:
        self._stations = stations
        self._cache: dict[tuple[float, float, int], tuple[float, list[Place]]] = {}

    async def execute(self, latitude: float, longitude: float, radius_m: int) -> list[Place]:
        require_service_area(latitude, longitude)
        if not 200 <= radius_m <= _MAX_RADIUS_M:
            raise InvalidDataError("El radio debe estar entre 200 m y 10 km")
        # Redondear a ~100 m deja que locales vecinos compartan la misma consulta.
        key = (round(latitude, 3), round(longitude, 3), radius_m)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < _CACHE_SECONDS:
            places = cached[1]
        else:
            places = await self._stations.around(latitude, longitude, radius_m)
            self._cache[key] = (time.monotonic(), places)
        return sorted(places, key=lambda place: place.distance_m)


class GetTile:
    def __init__(self, source: TileSource) -> None:
        self._source = source

    async def execute(self, z: int, x: int, y: int) -> bytes:
        if not tile_allowed(z, x, y):
            raise NotFoundError("El mapa solo cubre Pasto y el resto de Nariño")
        tile = await self._source.fetch(z, x, y)
        if tile is None:
            raise NotFoundError("El mosaico del mapa no está disponible")
        return tile
