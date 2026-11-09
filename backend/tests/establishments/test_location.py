"""La ubicación del local: a mano, con el GPS del navegador o por la dirección."""

import httpx
import pytest

from bandit.establishments.domain.models import GeoPoint
from bandit.establishments.infrastructure.nominatim import NominatimGeocoder
from bandit.establishments.module import EstablishmentsModule
from bandit.shared.errors import InvalidDataError


class FakeGeocoder:
    def __init__(self, point):
        self.point = point
        self.queries: list[str] = []

    async def locate(self, address):
        self.queries.append(address)
        return self.point


async def test_location_is_saved_and_read_back(sessions):
    module = EstablishmentsModule(sessions)
    local = await module.create.execute("La Perla Negra", "Calle 18 # 25-30")

    await module.set_location.execute(local.id, GeoPoint(1.2136, -77.2811))

    assert (await module.get.execute(local.id)).location == GeoPoint(1.2136, -77.2811)


async def test_address_without_city_is_searched_in_pasto(sessions):
    geocoder = FakeGeocoder(GeoPoint(1.21, -77.28))
    module = EstablishmentsModule(sessions, geocoder)
    local = await module.create.execute("Bar", "Calle 18 # 25-30")

    located = await module.locate_by_address.execute(local.id)

    assert geocoder.queries == ["Calle 18 # 25-30, Pasto, Nariño, Colombia"]
    assert located.location == GeoPoint(1.21, -77.28)


async def test_unknown_address_explains_what_to_do(sessions):
    module = EstablishmentsModule(sessions, FakeGeocoder(None))
    local = await module.create.execute("Bar", "Dirección inexistente")

    with pytest.raises(InvalidDataError, match="ubicación actual"):
        await module.locate_by_address.execute(local.id)


def test_rejects_impossible_coordinates():
    with pytest.raises(InvalidDataError):
        GeoPoint(120, -77)


async def test_nominatim_identifies_itself_and_caches():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.headers["User-Agent"] == "Bandit/test"
        return httpx.Response(200, json=[{"lat": "1.2136", "lon": "-77.2811"}])

    geocoder = NominatimGeocoder("Bandit/test", transport=httpx.MockTransport(handler))

    assert await geocoder.locate("Calle 18, Pasto") == GeoPoint(1.2136, -77.2811)
    assert await geocoder.locate("calle 18,  pasto") == GeoPoint(1.2136, -77.2811)
    assert len(calls) == 1
