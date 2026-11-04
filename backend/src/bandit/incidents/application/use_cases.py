"""Casos de uso de incidentes."""

from datetime import timedelta
from uuid import UUID, uuid4

from bandit.analysis.public import SituationDetected
from bandit.establishments.public import GetEstablishment
from bandit.incidents.domain.models import Incident, IncidentChanged, IncidentConfirmed
from bandit.incidents.domain.ports import EvidenceStore, IncidentRepository
from bandit.shared.clock import Clock
from bandit.shared.errors import ConflictError, NotFoundError
from bandit.shared.events import EventBus


class GetIncident:
    def __init__(self, incidents: IncidentRepository) -> None:
        self._incidents = incidents

    async def execute(self, incident_id: UUID) -> Incident:
        incident = await self._incidents.get(incident_id)
        if incident is None:
            raise NotFoundError("El incidente no existe")
        return incident


class ListIncidents:
    def __init__(self, incidents: IncidentRepository) -> None:
        self._incidents = incidents

    async def execute(self, establishment_id: UUID, limit: int = 100) -> list[Incident]:
        return await self._incidents.list_recent(establishment_id, limit)


class RecordSituation:
    """Convierte una detección en incidente pendiente. Nunca avisa a nadie externo."""

    def __init__(
        self, incidents: IncidentRepository, evidence: EvidenceStore, bus: EventBus
    ) -> None:
        self._incidents = incidents
        self._evidence = evidence
        self._bus = bus

    async def execute(self, event: SituationDetected) -> Incident:
        assessment = event.assessment
        incident = Incident(
            id=uuid4(),
            establishment_id=event.establishment_id,
            camera_id=event.camera_id,
            camera_name=event.camera_name,
            type=assessment.type.value,
            severity=assessment.severity.value,
            confidence=assessment.confidence,
            description=assessment.description,
            detected_at=event.detected_at,
        )
        await self._incidents.add(incident)
        await self._evidence.save(incident.id, event.evidence_jpeg)
        await self._bus.publish(IncidentChanged(incident=incident))
        return incident


class ConfirmIncident:
    """Paso humano obligatorio: es el único camino hacia una alerta al CAI."""

    def __init__(
        self,
        incidents: IncidentRepository,
        get: GetIncident,
        establishments: GetEstablishment,
        bus: EventBus,
        clock: Clock,
    ) -> None:
        self._incidents = incidents
        self._get = get
        self._establishments = establishments
        self._bus = bus
        self._clock = clock

    async def execute(self, incident_id: UUID, operator_email: str) -> Incident:
        incident = await self._get.execute(incident_id)
        establishment = await self._establishments.execute(incident.establishment_id)
        if establishment.cai_whatsapp is None:
            raise ConflictError("Agrega el WhatsApp del CAI en los ajustes del local")
        incident.confirm(self._clock.now(), operator_email)
        await self._incidents.save(incident)
        await self._bus.publish(IncidentChanged(incident=incident))
        await self._bus.publish(IncidentConfirmed(incident=incident, confirmed_by=operator_email))
        return incident


class DiscardIncident:
    def __init__(
        self, incidents: IncidentRepository, get: GetIncident, bus: EventBus, clock: Clock
    ) -> None:
        self._incidents = incidents
        self._get = get
        self._bus = bus
        self._clock = clock

    async def execute(self, incident_id: UUID, operator_email: str) -> Incident:
        incident = await self._get.execute(incident_id)
        incident.discard(self._clock.now(), operator_email)
        await self._incidents.save(incident)
        await self._bus.publish(IncidentChanged(incident=incident))
        return incident


class RecordDelivery:
    """Registra el resultado del envío que hizo el módulo de notificaciones."""

    def __init__(
        self, incidents: IncidentRepository, get: GetIncident, bus: EventBus, clock: Clock
    ) -> None:
        self._incidents = incidents
        self._get = get
        self._bus = bus
        self._clock = clock

    async def delivered(self, incident_id: UUID) -> None:
        incident = await self._get.execute(incident_id)
        incident.mark_notified(self._clock.now())
        await self._finish(incident)

    async def failed(self, incident_id: UUID) -> None:
        incident = await self._get.execute(incident_id)
        incident.mark_notification_failed(self._clock.now())
        await self._finish(incident)

    async def _finish(self, incident: Incident) -> None:
        await self._incidents.save(incident)
        await self._bus.publish(IncidentChanged(incident=incident))


class PurgeEvidence:
    def __init__(self, evidence: EvidenceStore, clock: Clock, retention: timedelta) -> None:
        self._evidence = evidence
        self._clock = clock
        self._retention = retention

    async def execute(self) -> int:
        return await self._evidence.purge_older_than(self._clock.now() - self._retention)
