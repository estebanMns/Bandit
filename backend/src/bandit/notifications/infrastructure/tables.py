"""Tabla de suscripciones Web Push."""

from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from bandit.shared.db import Base


class PushTargetRow(Base):
    __tablename__ = "push_targets"

    endpoint: Mapped[str] = mapped_column(String(1000), primary_key=True)
    establishment_id: Mapped[UUID] = mapped_column(
        ForeignKey("establishments.id", ondelete="CASCADE"), index=True
    )
    p256dh: Mapped[str] = mapped_column(String(200))
    auth: Mapped[str] = mapped_column(String(100))
