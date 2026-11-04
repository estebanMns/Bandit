"""Puertos del módulo de incidentes."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from bandit.incidents.domain.models import Incident


class IncidentRepository(Protocol):
    async def add(self, incident: Incident) -> None: ...

    async def save(self, incident: Incident) -> None: ...

    async def get(self, incident_id: UUID) -> Incident | None: ...

    async def list_recent(self, establishment_id: UUID, limit: int) -> list[Incident]: ...


class EvidenceStore(Protocol):
    async def save(self, incident_id: UUID, jpeg: bytes) -> None: ...

    async def load(self, incident_id: UUID) -> bytes | None: ...

    async def purge_older_than(self, cutoff: datetime) -> int: ...
