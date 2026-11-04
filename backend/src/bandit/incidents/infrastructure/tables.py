"""Tablas de incidentes y auditoría."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bandit.shared.db import Base, UtcDateTime


class IncidentRow(Base):
    __tablename__ = "incidents"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    establishment_id: Mapped[UUID] = mapped_column(
        ForeignKey("establishments.id", ondelete="CASCADE"), index=True
    )
    camera_id: Mapped[UUID] = mapped_column(index=True)
    camera_name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(10))
    confidence: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(300))
    detected_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    status: Mapped[str] = mapped_column(String(30))
    audit: Mapped[list["AuditRow"]] = relationship(
        order_by="AuditRow.position", cascade="all, delete-orphan", lazy="selectin"
    )


class AuditRow(Base):
    __tablename__ = "incident_audit"

    incident_id: Mapped[UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(30))
    at: Mapped[datetime] = mapped_column(UtcDateTime)
    actor: Mapped[str] = mapped_column(String(320))
