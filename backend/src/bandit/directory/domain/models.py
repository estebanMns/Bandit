"""Registro del directorio: texto publicado por la Policía Nacional, con su fuente."""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


def normalize_text(text: str) -> str:
    """Forma comparable: sin mayúsculas, tildes ni espacios repetidos."""
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.casefold().split())


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalize_text(text)).strip("-")


@dataclass(frozen=True, slots=True)
class ExtractedRecord:
    """Lo que el agente dice haber leído. No es confiable hasta verificarlo."""

    name: str
    alias: str | None
    crime: str | None
    reward: str | None
    region: str | None
    hotline_email: str | None
    hotline_phones: tuple[str, ...]
    photo_url: str | None
    flyer_url: str | None


@dataclass(slots=True)
class WantedRecord:
    id: UUID
    slug: str
    name: str
    alias: str | None
    crime: str | None
    reward: str | None
    region: str | None
    hotline_email: str | None
    hotline_phones: list[str] = field(default_factory=list)
    photo_file: str | None = None
    flyer_file: str | None = None
    source_url: str = ""
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    active: bool = True


@dataclass(frozen=True, slots=True)
class SyncReport:
    published: int
    rejected: int
    retired: int
    completed: bool
