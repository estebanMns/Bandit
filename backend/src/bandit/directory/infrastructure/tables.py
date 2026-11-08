"""Tablas del directorio. No guardan vectores ni datos biométricos."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from bandit.shared.db import Base, UtcDateTime


class WantedRow(Base):
    __tablename__ = "wanted_records"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    alias: Mapped[str | None] = mapped_column(String(300))
    crime: Mapped[str | None] = mapped_column(String(300))
    reward: Mapped[str | None] = mapped_column(String(200))
    region: Mapped[str | None] = mapped_column(String(200))
    hotline_email: Mapped[str | None] = mapped_column(String(320))
    hotline_phones: Mapped[list[str]] = mapped_column(JSON)
    photo_file: Mapped[str | None] = mapped_column(String(320))
    flyer_file: Mapped[str | None] = mapped_column(String(320))
    source_url: Mapped[str] = mapped_column(String(500))
    first_seen_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    last_seen_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    active: Mapped[bool] = mapped_column(index=True)


class SyncRunRow(Base):
    __tablename__ = "directory_sync_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trigger: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    published: Mapped[int]
    rejected: Mapped[int]
    retired: Mapped[int]
    completed: Mapped[bool]
    error: Mapped[str | None] = mapped_column(String(300))
