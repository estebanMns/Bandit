"""Registro del directorio: texto publicado por la Policía Nacional, con su fuente."""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
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
    # Lo fija el código según el orden en la página de la Policía, no el modelo.
    listing_position: int | None = None


# Fuente de los registros de prueba creados a mano en este equipo, nunca por la Policía.
LOCAL_TEST_SOURCE = "prueba-local"


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
    reward_amount: int | None = None
    listing_position: int | None = None

    @property
    def local_test(self) -> bool:
        return self.source_url == LOCAL_TEST_SOURCE


@dataclass(frozen=True, slots=True)
class SyncReport:
    published: int
    rejected: int
    retired: int
    completed: bool
    pages_failed: int = 0
    error: str | None = None


class SyncTrigger(StrEnum):
    STARTUP = "startup"
    SCHEDULED = "scheduled"
    MANUAL = "manual"


@dataclass(slots=True)
class SyncRun:
    """Una corrida de extracción: cuándo, por qué y qué resultó."""

    id: UUID
    trigger: SyncTrigger
    started_at: datetime
    finished_at: datetime | None = None
    published: int = 0
    rejected: int = 0
    retired: int = 0
    completed: bool = False
    error: str | None = None
    pages_failed: int = 0


_AMOUNT = re.compile(
    r"(\d[\d.,]*)\s*(millones|millón|millon|mil|smlmv|smmlv|salarios? m[ií]nimos?)?", re.IGNORECASE
)
_MINIMUM_WAGES = ("smlmv", "smmlv", "salario")

# Salario mínimo legal mensual en pesos (2025). Cambia cada año: se ajusta con SMLMV_COP.
DEFAULT_SMLMV_COP = 1_423_500


def parse_reward(text: str | None, smlmv_cop: int = DEFAULT_SMLMV_COP) -> int | None:
    """Convierte la recompensa publicada en pesos: "10 millones" -> 10000000.

    También entiende salarios mínimos: "3.076 SMLMV" -> 3076 x salario mínimo.
    Devuelve None si no hay monto ("No Aplica", vacío o algo que no se entiende).
    """
    if not text:
        return None
    match = _AMOUNT.search(text)
    if match is None:
        return None
    digits, unit = match.group(1), (match.group(2) or "").lower()
    if unit.startswith(_MINIMUM_WAGES):
        wages = int(re.sub(r"[.,]", "", digits))
        return wages * smlmv_cop if wages > 0 else None
    if unit:
        # "1,5 millones" o "1.5 millones" es decimal; "1.500 millones" usa punto de miles.
        if re.fullmatch(r"\d+[.,]\d{1,2}", digits):
            number = float(digits.replace(",", "."))
        else:
            number = float(re.sub(r"[.,]", "", digits))
        factor = 1_000 if unit == "mil" else 1_000_000
        amount = int(number * factor)
    else:
        amount = int(re.sub(r"[.,]", "", digits))
    return amount if amount > 0 else None


# Gravedad del delito publicado, de mayor a menor. Es una lista fija y visible,
# no una calificación de la persona: solo ordena lo que la Policía ya publicó.
CRIME_LEVELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Homicidio", ("homicidio", "feminicidio", "asesinato", "masacre")),
    ("Secuestro, extorsión o terrorismo", ("secuestro", "extorsion", "terrorismo", "rebelion")),
    ("Delito sexual", ("sexual", "acceso carnal")),
    (
        "Tráfico, armas o concierto para delinquir",
        ("trafico", "estupefacientes", "narcotrafico", "armas", "concierto para delinquir"),
    ),
    ("Hurto u otros", ("hurto", "robo", "lesiones", "estafa")),
)


def crime_level(crime: str | None) -> int:
    """Posición en CRIME_LEVELS; los delitos sin dato o no listados van al final."""
    if crime:
        normalized = normalize_text(crime)
        for level, (_, words) in enumerate(CRIME_LEVELS):
            if any(word in normalized for word in words):
                return level
    return len(CRIME_LEVELS)


def priority_key(record: WantedRecord) -> tuple[int, int, int, str]:
    """Recompensa mayor primero, luego delito más grave, luego orden de la Policía."""
    return (
        -(record.reward_amount or 0),
        crime_level(record.crime),
        record.listing_position if record.listing_position is not None else 1_000_000,
        record.name,
    )
