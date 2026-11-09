"""Repositorio SQL de locales."""

from uuid import UUID

from sqlalchemy import select

from bandit.establishments.domain.models import Establishment, GeoPoint, WhatsAppNumber
from bandit.establishments.infrastructure.tables import EstablishmentRow
from bandit.shared.db import SessionFactory


def _to_model(row: EstablishmentRow) -> Establishment:
    return Establishment(
        id=row.id,
        name=row.name,
        address=row.address,
        cai_whatsapp=WhatsAppNumber(row.cai_whatsapp) if row.cai_whatsapp else None,
        location=(
            GeoPoint(row.latitude, row.longitude)
            if row.latitude is not None and row.longitude is not None
            else None
        ),
    )


class SqlEstablishmentRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    async def add(self, establishment: Establishment) -> None:
        async with self._sessions.begin() as session:
            session.add(
                EstablishmentRow(
                    id=establishment.id,
                    name=establishment.name,
                    address=establishment.address,
                    cai_whatsapp=_number(establishment),
                    latitude=establishment.location.latitude if establishment.location else None,
                    longitude=establishment.location.longitude if establishment.location else None,
                )
            )

    async def save(self, establishment: Establishment) -> None:
        async with self._sessions.begin() as session:
            row = await session.get(EstablishmentRow, establishment.id)
            if row is not None:
                row.name = establishment.name
                row.address = establishment.address
                row.cai_whatsapp = _number(establishment)
                location = establishment.location
                row.latitude = location.latitude if location else None
                row.longitude = location.longitude if location else None

    async def get(self, establishment_id: UUID) -> Establishment | None:
        async with self._sessions() as session:
            row = await session.get(EstablishmentRow, establishment_id)
            return _to_model(row) if row else None

    async def list_all(self) -> list[Establishment]:
        async with self._sessions() as session:
            rows = await session.scalars(select(EstablishmentRow).order_by(EstablishmentRow.name))
            return [_to_model(row) for row in rows]


def _number(establishment: Establishment) -> str | None:
    return establishment.cai_whatsapp.value if establishment.cai_whatsapp else None
