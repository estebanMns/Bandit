"""Tabla de locales."""

from uuid import UUID

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from bandit.shared.db import Base


class EstablishmentRow(Base):
    __tablename__ = "establishments"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(300))
    cai_whatsapp: Mapped[str | None] = mapped_column(String(16))
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
