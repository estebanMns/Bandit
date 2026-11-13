"""Mensajes y resultados de envío."""

from dataclasses import dataclass
from uuid import UUID

from bandit.shared.events import DomainEvent

SITUATION_LABELS = {
    "weapon": "Arma visible",
    "robbery": "Atraco o hurto",
    "fight": "Pelea",
    "fire": "Fuego o humo",
    "medical": "Emergencia de salud",
    "wanted_match": "Persona buscada identificada",
}


@dataclass(frozen=True, slots=True)
class AlertMessage:
    """Contenido de la alerta. No lleva imágenes ni datos de personas."""

    establishment: str
    address: str
    situation: str
    time: str
    description: str


@dataclass(frozen=True, slots=True)
class PushTarget:
    endpoint: str
    p256dh: str
    auth: str


@dataclass(frozen=True, slots=True, kw_only=True)
class AlertDelivered(DomainEvent):
    incident_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class AlertFailed(DomainEvent):
    incident_id: UUID


class PushTargetGoneError(Exception):
    """El navegador revocó la suscripción."""
