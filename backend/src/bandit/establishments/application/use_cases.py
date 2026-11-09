"""Casos de uso de locales."""

from uuid import UUID, uuid4

from bandit.establishments.domain.models import Establishment, GeoPoint, WhatsAppNumber
from bandit.establishments.domain.ports import EstablishmentRepository, Geocoder
from bandit.shared.errors import InvalidDataError, NotFoundError

# Si la dirección no dice la ciudad, se asume la del proyecto.
DEFAULT_CITY = "Pasto, Nariño, Colombia"


class CreateEstablishment:
    def __init__(self, establishments: EstablishmentRepository) -> None:
        self._establishments = establishments

    async def execute(self, name: str, address: str) -> Establishment:
        establishment = Establishment(id=uuid4(), name=name.strip(), address=address.strip())
        await self._establishments.add(establishment)
        return establishment


class GetEstablishment:
    def __init__(self, establishments: EstablishmentRepository) -> None:
        self._establishments = establishments

    async def execute(self, establishment_id: UUID) -> Establishment:
        establishment = await self._establishments.get(establishment_id)
        if establishment is None:
            raise NotFoundError("El local no existe")
        return establishment


class ListEstablishments:
    def __init__(self, establishments: EstablishmentRepository) -> None:
        self._establishments = establishments

    async def execute(self) -> list[Establishment]:
        return await self._establishments.list_all()


class SetCaiWhatsApp:
    """Registra o quita el número al que se enviarán las alertas confirmadas."""

    def __init__(self, establishments: EstablishmentRepository, get: GetEstablishment) -> None:
        self._establishments = establishments
        self._get = get

    async def execute(self, establishment_id: UUID, raw_number: str | None) -> Establishment:
        establishment = await self._get.execute(establishment_id)
        establishment.cai_whatsapp = WhatsAppNumber.parse(raw_number) if raw_number else None
        await self._establishments.save(establishment)
        return establishment


class SetLocation:
    """Guarda la ubicación del local, elegida en el mapa o con el GPS del navegador."""

    def __init__(self, establishments: EstablishmentRepository, get: GetEstablishment) -> None:
        self._establishments = establishments
        self._get = get

    async def execute(self, establishment_id: UUID, point: GeoPoint) -> Establishment:
        establishment = await self._get.execute(establishment_id)
        establishment.location = point
        await self._establishments.save(establishment)
        return establishment


class LocateByAddress:
    """Ubica el local a partir de su dirección registrada."""

    def __init__(
        self, geocoder: Geocoder, get: GetEstablishment, set_location: SetLocation
    ) -> None:
        self._geocoder = geocoder
        self._get = get
        self._set_location = set_location

    async def execute(self, establishment_id: UUID) -> Establishment:
        establishment = await self._get.execute(establishment_id)
        query = establishment.address
        if "pasto" not in query.lower() and "colombia" not in query.lower():
            query = f"{query}, {DEFAULT_CITY}"
        point = await self._geocoder.locate(query)
        if point is None:
            raise InvalidDataError(
                "No se encontró esa dirección en el mapa. "
                "Usa tu ubicación actual o escríbela completa."
            )
        return await self._set_location.execute(establishment_id, point)
