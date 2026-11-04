"""Casos de uso de locales."""

from uuid import UUID, uuid4

from bandit.establishments.domain.models import Establishment, WhatsAppNumber
from bandit.establishments.domain.ports import EstablishmentRepository
from bandit.shared.errors import NotFoundError


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
