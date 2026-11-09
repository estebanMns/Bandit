"""Geocodificación con Nominatim de OpenStreetMap, respetando su política de uso.

Política: máximo un pedido por segundo, User-Agent que identifique la aplicación y
resultados en caché. https://operations.osmfoundation.org/policies/nominatim/
"""

import asyncio
import time

import httpx

from bandit.establishments.domain.models import GeoPoint

_MIN_INTERVAL_SECONDS = 1.1


class NominatimGeocoder:
    def __init__(
        self,
        user_agent: str,
        url: str = "https://nominatim.openstreetmap.org/search",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._user_agent = user_agent
        self._url = url
        self._transport = transport
        self._cache: dict[str, GeoPoint | None] = {}
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def locate(self, address: str) -> GeoPoint | None:
        key = " ".join(address.lower().split())
        if key in self._cache:
            return self._cache[key]
        async with self._lock:
            wait = _MIN_INTERVAL_SECONDS - (time.monotonic() - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                async with httpx.AsyncClient(transport=self._transport, timeout=15) as client:
                    response = await client.get(
                        self._url,
                        params={"q": address, "format": "jsonv2", "limit": 1, "countrycodes": "co"},
                        headers={"User-Agent": self._user_agent, "Accept-Language": "es"},
                    )
            finally:
                self._last = time.monotonic()
        response.raise_for_status()
        results = response.json()
        point = (
            GeoPoint(float(results[0]["lat"]), float(results[0]["lon"]))
            if isinstance(results, list) and results
            else None
        )
        self._cache[key] = point
        return point
