"""Puertos del módulo de locales."""

from typing import Protocol
from uuid import UUID

from bandit.establishments.domain.models import Establishment, GeoPoint


class EstablishmentRepository(Protocol):
    async def add(self, establishment: Establishment) -> None: ...

    async def save(self, establishment: Establishment) -> None: ...

    async def get(self, establishment_id: UUID) -> Establishment | None: ...

    async def list_all(self) -> list[Establishment]: ...


class Geocoder(Protocol):
    """Convierte una dirección en coordenadas. None si no la encuentra."""

    async def locate(self, address: str) -> GeoPoint | None: ...
