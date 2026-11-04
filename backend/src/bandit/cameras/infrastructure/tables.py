"""Tabla de cámaras."""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bandit.shared.db import Base


class CameraRow(Base):
    __tablename__ = "cameras"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    establishment_id: Mapped[UUID] = mapped_column(
        ForeignKey("establishments.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    encrypted_url: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool]
