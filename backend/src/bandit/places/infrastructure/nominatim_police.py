"""Estaciones de policía y CAI con la búsqueda de Nominatim (OpenStreetMap).

Se buscan los puntos con etiqueta amenity=police dentro de un recuadro alrededor del
local. En la red del proyecto, Overpass no respondía y Nominatim sí, con los CAI de Pasto.
"""

import math
from typing import Any

import httpx

from bandit.places.domain.models import Place, distance_m
from bandit.shared.nominatim_gate import nominatim_turn

_METERS_PER_DEGREE = 111_320
_QUERIES = ("police", "CAI")


def viewbox(latitude: float, longitude: float, radius_m: int) -> str:
    """Recuadro "oeste,norte,este,sur" que contiene el círculo de búsqueda."""
    dlat = radius_m / _METERS_PER_DEGREE
    dlng = radius_m / (_METERS_PER_DEGREE * max(math.cos(math.radians(latitude)), 0.01))
    return f"{longitude - dlng},{latitude + dlat},{longitude + dlng},{latitude - dlat}"


def police_places(
    results: list[dict[str, Any]], latitude: float, longitude: float, radius_m: int
) -> list[Place]:
    places: dict[str, Place] = {}
    for item in results:
        if item.get("category") != "amenity" or item.get("type") != "police":
            continue
        point_lat, point_lng = float(item["lat"]), float(item["lon"])
        distance = distance_m(latitude, longitude, point_lat, point_lng)
        if distance > radius_m:
            continue
        key = str(item.get("osm_id") or f"{point_lat},{point_lng}")
        places[key] = Place(
            name=str(item.get("name") or "Estación de policía"),
            latitude=point_lat,
            longitude=point_lng,
            distance_m=distance,
        )
    return list(places.values())


class NominatimPoliceStations:
    def __init__(
        self,
        user_agent: str,
        url: str = "https://nominatim.openstreetmap.org/search",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._user_agent = user_agent
        self._url = url
        self._transport = transport

    async def around(self, latitude: float, longitude: float, radius_m: int) -> list[Place]:
        results: list[dict[str, Any]] = []
        box = viewbox(latitude, longitude, radius_m)
        async with httpx.AsyncClient(transport=self._transport, timeout=15) as client:
            for query in _QUERIES:
                async with nominatim_turn():
                    response = await client.get(
                        self._url,
                        params={
                            "q": query,
                            "format": "jsonv2",
                            "limit": 50,
                            "viewbox": box,
                            "bounded": 1,
                        },
                        headers={"User-Agent": self._user_agent, "Accept-Language": "es"},
                    )
                response.raise_for_status()
                page = response.json()
                if isinstance(page, list):
                    results.extend(item for item in page if isinstance(item, dict))
        return police_places(results, latitude, longitude, radius_m)
