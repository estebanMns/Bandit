"""Mapa de Pasto y CAI cercanos con datos de OpenStreetMap, sin volverse un proxy abierto."""

import httpx
import pytest

from bandit.places.application.use_cases import FindNearbyCai, GetTile
from bandit.places.domain.models import PASTO, distance_m, tile_allowed
from bandit.places.infrastructure.osm_tiles import CachedOsmTiles
from bandit.places.infrastructure.overpass import OverpassPoliceStations, places_from
from bandit.shared.errors import InvalidDataError, NotFoundError

LAT, LNG = PASTO
OVERPASS = {
    "elements": [
        {"type": "node", "lat": 1.2140, "lon": -77.2800, "tags": {"name": "CAI Centro"}},
        {"type": "way", "center": {"lat": 1.2300, "lon": -77.2900}, "tags": {}},
        {"type": "node", "tags": {"name": "Sin coordenadas"}},
    ]
}


def test_distance_between_two_points_in_pasto():
    assert 100 <= distance_m(LAT, LNG, 1.2140, -77.2800) <= 140
    assert distance_m(LAT, LNG, LAT, LNG) == 0


def test_reads_police_stations_from_overpass():
    places = places_from(OVERPASS, LAT, LNG)

    assert [p.name for p in places] == ["CAI Centro", "Estación de policía"]
    assert places[0].distance_m < places[1].distance_m


class CountingStations:
    def __init__(self):
        self.calls = 0

    async def around(self, latitude, longitude, radius_m):
        self.calls += 1
        return list(reversed(places_from(OVERPASS, latitude, longitude)))


async def test_nearest_first_and_cached():
    stations = CountingStations()
    find = FindNearbyCai(stations)

    first = await find.execute(LAT, LNG, 5000)
    await find.execute(LAT + 0.0001, LNG, 5000)

    assert [p.name for p in first] == ["CAI Centro", "Estación de policía"]
    assert stations.calls == 1


@pytest.mark.parametrize(("lat", "lng", "radius"), [(4.71, -74.07, 5000), (LAT, LNG, 50_000)])
async def test_rejects_points_outside_narino_or_huge_radius(lat, lng, radius):
    with pytest.raises(InvalidDataError):
        await FindNearbyCai(CountingStations()).execute(lat, lng, radius)


def test_tiles_only_inside_the_service_area():
    assert tile_allowed(13, 2335, 4068)  # Pasto
    assert not tile_allowed(13, 2390, 3960)  # Bogotá
    assert not tile_allowed(3, 2, 3)  # zoom demasiado lejano
    assert not tile_allowed(13, -1, 4068)


async def test_overpass_client_sends_the_query():
    def handler(request: httpx.Request) -> httpx.Response:
        assert b"amenity" in request.content and request.headers["User-Agent"] == "Bandit/test"
        return httpx.Response(200, json=OVERPASS)

    stations = OverpassPoliceStations("Bandit/test", transport=httpx.MockTransport(handler))

    assert len(await stations.around(LAT, LNG, 3000)) == 2


async def test_tiles_are_downloaded_once_and_then_served_from_disk(tmp_path):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=b"\x89PNG fake")

    tiles = CachedOsmTiles(str(tmp_path), "Bandit/test", transport=httpx.MockTransport(handler))
    get = GetTile(tiles)

    assert (await get.execute(13, 2335, 4068)).startswith(b"\x89PNG")
    await get.execute(13, 2335, 4068)

    assert len(calls) == 1
    with pytest.raises(NotFoundError):
        await get.execute(13, 2390, 3960)
