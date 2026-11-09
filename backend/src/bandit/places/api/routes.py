"""Rutas de lugares: CAI cercanos y mosaicos del mapa. Requieren sesión."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel

from bandit.identity.public import CurrentUser
from bandit.places.domain.models import Place
from bandit.places.module import PlacesModule

router = APIRouter(prefix="/api", tags=["places"])

ATTRIBUTION = "© colaboradores de OpenStreetMap"


def _module(request: Request) -> PlacesModule:
    module: PlacesModule = request.app.state.places
    return module


Module = Annotated[PlacesModule, Depends(_module)]


class PlaceResponse(BaseModel):
    name: str
    latitude: float
    longitude: float
    distance_m: int

    @classmethod
    def of(cls, place: Place) -> "PlaceResponse":
        return cls(
            name=place.name,
            latitude=place.latitude,
            longitude=place.longitude,
            distance_m=place.distance_m,
        )


class NearbyResponse(BaseModel):
    source: str
    places: list[PlaceResponse]


@router.get("/places/nearby-cai")
async def nearby_cai(
    _: CurrentUser,
    module: Module,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    radius: Annotated[int, Query()] = 5_000,
) -> NearbyResponse:
    places = await module.nearby_cai.execute(lat, lng, radius)
    return NearbyResponse(source=ATTRIBUTION, places=[PlaceResponse.of(p) for p in places])


@router.get("/map/tiles/{z}/{x}/{y}.png")
async def map_tile(z: int, x: int, y: int, _: CurrentUser, module: Module) -> Response:
    tile = await module.tile.execute(z, x, y)
    return Response(
        tile,
        media_type="image/png",
        headers={
            "Cache-Control": "private, max-age=86400",
            "Cross-Origin-Resource-Policy": "same-origin",
            "X-Content-Type-Options": "nosniff",
        },
    )
