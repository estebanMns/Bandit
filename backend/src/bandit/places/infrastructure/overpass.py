"""Estaciones de policía y CAI desde Overpass (OpenStreetMap). Datos públicos y abiertos."""

from typing import Any

import httpx

from bandit.places.domain.models import Place, distance_m

_QUERY = """[out:json][timeout:25];
(
  node["amenity"="police"](around:{radius},{lat},{lng});
  way["amenity"="police"](around:{radius},{lat},{lng});
);
out center tags;"""


def _coordinates(element: dict[str, Any]) -> tuple[float, float] | None:
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center")
    if isinstance(center, dict) and "lat" in center and "lon" in center:
        return float(center["lat"]), float(center["lon"])
    return None


def places_from(data: dict[str, Any], latitude: float, longitude: float) -> list[Place]:
    places: list[Place] = []
    for element in data.get("elements", []):
        if not isinstance(element, dict):
            continue
        point = _coordinates(element)
        if point is None:
            continue
        tags = element.get("tags") or {}
        name = tags.get("name") or tags.get("official_name") or "Estación de policía"
        places.append(
            Place(
                name=str(name),
                latitude=point[0],
                longitude=point[1],
                distance_m=distance_m(latitude, longitude, point[0], point[1]),
            )
        )
    return places


class OverpassPoliceStations:
    def __init__(
        self,
        user_agent: str,
        url: str = "https://overpass-api.de/api/interpreter",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._user_agent = user_agent
        self._url = url
        self._transport = transport

    async def around(self, latitude: float, longitude: float, radius_m: int) -> list[Place]:
        query = _QUERY.format(radius=radius_m, lat=latitude, lng=longitude)
        async with httpx.AsyncClient(transport=self._transport, timeout=30) as client:
            response = await client.post(
                self._url, data={"data": query}, headers={"User-Agent": self._user_agent}
            )
        response.raise_for_status()
        return places_from(response.json(), latitude, longitude)
