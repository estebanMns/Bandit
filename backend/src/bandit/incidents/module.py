"""Composición del módulo de incidentes."""

from bandit.establishments.public import GetEstablishment, ListEstablishments
from bandit.incidents.application.use_cases import (
    ConfirmIncident,
    DiscardIncident,
    GetIncident,
    ListIncidents,
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
        list_establishments: ListEstablishments,
    ) -> None:
        repository = SqlIncidentRepository(sessions)
        self.evidence = evidence
        self.list_establishments = list_establishments
        self.get = GetIncident(repository)
        self.list_recent = ListIncidents(repository)
        self.record_situation = RecordSituation(repository, evidence, bus)
        self.confirm = ConfirmIncident(repository, self.get, establishments, bus, clock)
        self.discard = DiscardIncident(repository, self.get, bus, clock)
        self.record_delivery = RecordDelivery(repository, self.get, bus, clock)
