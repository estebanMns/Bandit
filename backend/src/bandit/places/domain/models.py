"""Puntos en el mapa, distancias y la zona que Bandit cubre."""

import math
from dataclasses import dataclass

from bandit.shared.errors import InvalidDataError

_EARTH_RADIUS_M = 6_371_000

# Nariño, con margen. El mapa y la búsqueda de CAI solo trabajan aquí: así los servicios
# de OpenStreetMap no se usan como un proxy abierto para cualquier parte del mundo.
SERVICE_AREA = (0.0, -79.5, 3.0, -76.5)  # sur, oeste, norte, este
PASTO = (1.2136, -77.2811)
MIN_ZOOM, MAX_ZOOM = 10, 18


@dataclass(frozen=True, slots=True)
class Place:
    name: str
    latitude: float
    longitude: float
    distance_m: int


def inside_service_area(latitude: float, longitude: float) -> bool:
    south, west, north, east = SERVICE_AREA
    return south <= latitude <= north and west <= longitude <= east


def require_service_area(latitude: float, longitude: float) -> None:
    if not inside_service_area(latitude, longitude):
        raise InvalidDataError("Por ahora el mapa solo cubre Pasto y el resto de Nariño")


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """Distancia en metros sobre la superficie de la Tierra (fórmula del haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a)))


def tile_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    """Sur, oeste, norte y este de un mosaico de mapa web (Web Mercator)."""
    n = 2**z

    def latitude(row: int) -> float:
        return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * row / n))))

    return latitude(y + 1), x / n * 360 - 180, latitude(y), (x + 1) / n * 360 - 180


def tile_allowed(z: int, x: int, y: int) -> bool:
    """El mosaico existe, está en un zoom útil y toca la zona de servicio."""
    if not MIN_ZOOM <= z <= MAX_ZOOM or not (0 <= x < 2**z and 0 <= y < 2**z):
        return False
    south, west, north, east = tile_bounds(z, x, y)
    area_south, area_west, area_north, area_east = SERVICE_AREA
    return south <= area_north and north >= area_south and west <= area_east and east >= area_west
