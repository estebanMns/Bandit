"""Composición del módulo de incidentes."""

from datetime import timedelta

from bandit.establishments.public import GetEstablishment
from bandit.incidents.application.use_cases import (
    ConfirmIncident,
    DiscardIncident,
    GetIncident,
    ListIncidents,
    PurgeEvidence,
    RecordDelivery,
    RecordSituation,
)
from bandit.incidents.domain.ports import EvidenceStore
from bandit.incidents.infrastructure.repositories import SqlIncidentRepository
from bandit.shared.clock import Clock
from bandit.shared.db import SessionFactory
from bandit.shared.events import EventBus


class IncidentsModule:
    def __init__(
        self,
        sessions: SessionFactory,
        evidence: EvidenceStore,
        establishments: GetEstablishment,
        bus: EventBus,
        clock: Clock,
        retention: timedelta,
    ) -> None:
        repository = SqlIncidentRepository(sessions)
        self.evidence = evidence
        self.get = GetIncident(repository)
        self.list_recent = ListIncidents(repository)
        self.record_situation = RecordSituation(repository, evidence, bus)
        self.confirm = ConfirmIncident(repository, self.get, establishments, bus, clock)
        self.discard = DiscardIncident(repository, self.get, bus, clock)
        self.record_delivery = RecordDelivery(repository, self.get, bus, clock)
        self.purge_evidence = PurgeEvidence(evidence, clock, retention)
