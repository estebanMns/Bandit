"""Composición del módulo de locales."""

from bandit.establishments.application.use_cases import (
    CreateEstablishment,
    GetEstablishment,
    ListEstablishments,
    LocateByAddress,
    SetCaiWhatsApp,
    SetLocation,
)
from bandit.establishments.domain.models import GeoPoint
from bandit.establishments.domain.ports import Geocoder
from bandit.establishments.infrastructure.repositories import SqlEstablishmentRepository
from bandit.shared.db import SessionFactory


class _NoGeocoder:
    """Sin servicio de mapas no se ubica por dirección; la ubicación se fija a mano."""

    async def locate(self, address: str) -> GeoPoint | None:
        return None


class EstablishmentsModule:
    def __init__(self, sessions: SessionFactory, geocoder: Geocoder | None = None) -> None:
        repository = SqlEstablishmentRepository(sessions)
        self.create = CreateEstablishment(repository)
        self.get = GetEstablishment(repository)
        self.list_all = ListEstablishments(repository)
        self.set_cai_whatsapp = SetCaiWhatsApp(repository, self.get)
        self.set_location = SetLocation(repository, self.get)
        self.locate_by_address = LocateByAddress(
            geocoder or _NoGeocoder(), self.get, self.set_location
        )
