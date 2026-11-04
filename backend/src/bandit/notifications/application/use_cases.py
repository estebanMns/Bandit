"""Entrega de alertas."""

import asyncio
import logging
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from bandit.establishments.public import Establishment, GetEstablishment
from bandit.incidents.public import IncidentChanged, IncidentConfirmed
from bandit.notifications.domain.models import (
    SITUATION_LABELS,
    AlertDelivered,
    AlertFailed,
    AlertMessage,
    PushTarget,
    PushTargetGoneError,
)
from bandit.notifications.domain.ports import AlertSender, PushSender, PushTargetRepository
from bandit.shared.clock import Clock
from bandit.shared.errors import ConflictError
from bandit.shared.events import EventBus

logger = logging.getLogger(__name__)

_COLOMBIA = ZoneInfo("America/Bogota")
_NEW_INCIDENT = "detected"


def _local_time(moment: datetime) -> str:
    return moment.astimezone(_COLOMBIA).strftime("%d/%m/%Y %H:%M")


class DeliverConfirmedAlert:
    """Se ejecuta solo con `IncidentConfirmed`, que exige la decisión de un operador."""

    def __init__(
        self,
        establishments: GetEstablishment,
        sender: AlertSender,
        bus: EventBus,
        retry_delays: Sequence[float] = (2.0, 10.0),
    ) -> None:
        self._establishments = establishments
        self._sender = sender
        self._bus = bus
        self._retry_delays = retry_delays

    async def execute(self, event: IncidentConfirmed) -> None:
        incident = event.incident
        establishment = await self._establishments.execute(incident.establishment_id)
        message = AlertMessage(
            establishment=establishment.name,
            address=establishment.address,
            situation=SITUATION_LABELS.get(incident.type, incident.type),
            time=_local_time(incident.detected_at),
            description=incident.description,
        )
        delivered = establishment.cai_whatsapp is not None and await self._send_with_retries(
            establishment.cai_whatsapp.value, message
        )
        result = AlertDelivered if delivered else AlertFailed
        await self._bus.publish(result(incident_id=incident.id))

    async def _send_with_retries(self, to: str, message: AlertMessage) -> bool:
        for delay in (*self._retry_delays, None):
            try:
                await self._sender.send(to, message)
                return True
            except Exception as error:
                logger.warning("Falló el envío por WhatsApp: %s", type(error).__name__)
                if delay is not None:
                    await asyncio.sleep(delay)
        return False


class SendTestMessage:
    def __init__(self, establishments: GetEstablishment, sender: AlertSender, clock: Clock) -> None:
        self._establishments = establishments
        self._sender = sender
        self._clock = clock

    async def execute(self, establishment_id: UUID) -> None:
        establishment = await self._establishments.execute(establishment_id)
        if establishment.cai_whatsapp is None:
            raise ConflictError("Guarda primero el WhatsApp del CAI")
        await self._sender.send(establishment.cai_whatsapp.value, self._message(establishment))

    def _message(self, establishment: Establishment) -> AlertMessage:
        return AlertMessage(
            establishment=establishment.name,
            address=establishment.address,
            situation="Mensaje de prueba",
            time=_local_time(self._clock.now()),
            description="Prueba de configuración. No hay ninguna emergencia.",
        )


class RegisterPushTarget:
    def __init__(self, targets: PushTargetRepository) -> None:
        self._targets = targets

    async def execute(self, establishment_id: UUID, target: PushTarget) -> None:
        await self._targets.add(establishment_id, target)


class PushNewIncident:
    """Avisa a los operadores con la app cerrada. Nunca sale del local."""

    def __init__(self, targets: PushTargetRepository, sender: PushSender) -> None:
        self._targets = targets
        self._sender = sender

    async def execute(self, event: IncidentChanged) -> None:
        incident = event.incident
        if incident.status.value != _NEW_INCIDENT:
            return
        title = SITUATION_LABELS.get(incident.type, "Situación detectada")
        body = f"{incident.camera_name}: revisa y decide si avisas al CAI."
        for target in await self._targets.list_for(incident.establishment_id):
            try:
                await self._sender.send(target, title, body, f"/incidentes/{incident.id}")
            except PushTargetGoneError:
                await self._targets.remove(target.endpoint)
            except Exception as error:
                logger.warning("Falló Web Push: %s", type(error).__name__)
