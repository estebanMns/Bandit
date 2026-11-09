"""Composición del módulo de lugares."""

from bandit.places.application.use_cases import FindNearbyCai, GetTile
from bandit.places.domain.ports import PoliceStations, TileSource


class PlacesModule:
    def __init__(self, stations: PoliceStations, tiles: TileSource) -> None:
        self.nearby_cai = FindNearbyCai(stations)
        self.tile = GetTile(tiles)
