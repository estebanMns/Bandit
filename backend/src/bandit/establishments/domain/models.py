"""El local y el número de WhatsApp del CAI que eligió."""

import re
from dataclasses import dataclass
from uuid import UUID

from bandit.shared.errors import InvalidDataError

_INTERNATIONAL_PHONE = re.compile(r"^\+[1-9]\d{7,14}$")
_SEPARATORS = re.compile(r"[\s()-]")


@dataclass(frozen=True, slots=True)
class WhatsAppNumber:
    """Número en formato internacional E.164."""

    value: str

    def __post_init__(self) -> None:
        if not _INTERNATIONAL_PHONE.fullmatch(self.value):
            raise InvalidDataError("Escribe el número en formato internacional, como +573001234567")

    @classmethod
    def parse(cls, raw: str) -> "WhatsAppNumber":
        return cls(_SEPARATORS.sub("", raw))


@dataclass(frozen=True, slots=True)
class GeoPoint:
    """Coordenadas WGS84 del local."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not (-90 <= self.latitude <= 90 and -180 <= self.longitude <= 180):
            raise InvalidDataError("Las coordenadas no son válidas")


@dataclass(slots=True)
class Establishment:
    id: UUID
    name: str
    address: str
    cai_whatsapp: WhatsAppNumber | None = None
    location: GeoPoint | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidDataError("El local necesita un nombre")
        if not self.address.strip():
            raise InvalidDataError("El local necesita una dirección")
