"""Geocodificación con Nominatim de OpenStreetMap, respetando su política de uso.

Política: máximo un pedido por segundo, User-Agent que identifique la aplicación y
resultados en caché. https://operations.osmfoundation.org/policies/nominatim/
"""

import httpx

from bandit.establishments.domain.models import GeoPoint
from bandit.shared.errors import UnavailableError
from bandit.shared.nominatim_gate import nominatim_turn


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

    async def locate(self, address: str) -> GeoPoint | None:
        key = " ".join(address.lower().split())
        if key in self._cache:
            return self._cache[key]
        try:
            async with (
                nominatim_turn(),
                httpx.AsyncClient(transport=self._transport, timeout=15) as client,
            ):
                response = await client.get(
                    self._url,
                    params={"q": address, "format": "jsonv2", "limit": 1, "countrycodes": "co"},
                    headers={"User-Agent": self._user_agent, "Accept-Language": "es"},
                )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise UnavailableError(
                "El servicio de mapas no respondió. Intenta de nuevo."
            ) from error
        results = response.json()
        point = (
            GeoPoint(float(results[0]["lat"]), float(results[0]["lon"]))
            if isinstance(results, list) and results
            else None
        )
        self._cache[key] = point
        return point
