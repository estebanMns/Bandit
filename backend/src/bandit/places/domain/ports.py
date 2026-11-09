"""Puertos del módulo de lugares."""

from typing import Protocol

from bandit.places.domain.models import Place


class PoliceStations(Protocol):
    """Estaciones de policía y CAI alrededor de un punto, según OpenStreetMap."""

    async def around(self, latitude: float, longitude: float, radius_m: int) -> list[Place]: ...


class TileSource(Protocol):
    """Mosaicos PNG del mapa base. None si el proveedor no lo entrega."""

    async def fetch(self, z: int, x: int, y: int) -> bytes | None: ...
