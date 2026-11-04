import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest

from bandit.analysis.public import SceneAssessment, Severity, SituationDetected, SituationType
from bandit.establishments.module import EstablishmentsModule
from bandit.incidents.domain.models import (
    Incident,
    IncidentChanged,
    IncidentConfirmed,
    IncidentStatus,
)
from bandit.incidents.infrastructure.file_evidence import FileEvidenceStore
from bandit.incidents.module import IncidentsModule
from bandit.shared.errors import ConflictError
from bandit.shared.events import InMemoryEventBus

OPERATOR = "ana@example.com"


@pytest.fixture
def bus():
    return InMemoryEventBus()


@pytest.fixture
def confirmed(bus):
    events: list[IncidentConfirmed] = []

    async def record(event: IncidentConfirmed) -> None:
        events.append(event)

    bus.subscribe(IncidentConfirmed, record)
    return events


@pytest.fixture
def establishments(sessions):
    return EstablishmentsModule(sessions)


@pytest.fixture
def module(sessions, establishments, bus, clock, tmp_path) -> IncidentsModule:
    return IncidentsModule(
        sessions,
        FileEvidenceStore(str(tmp_path)),
        establishments.get,
        bus,
        clock,
        timedelta(days=7),
    )


@pytest.fixture
async def local(establishments):
    created = await establishments.create.execute("Bar", "Calle 1")
    await establishments.set_cai_whatsapp.execute(created.id, "+573001234567")
    return created


def situation(establishment_id, clock) -> SituationDetected:
    return SituationDetected(
        camera_id=uuid4(),
        establishment_id=establishment_id,
        camera_name="Barra",
        assessment=SceneAssessment(SituationType.FIGHT, Severity.HIGH, 0.9, "Pelea en la barra."),
        evidence_jpeg=b"jpeg",
        detected_at=clock.now(),
    )


async def test_detection_stays_pending_and_authorizes_nothing(module, local, clock, confirmed):
    incident = await module.record_situation.execute(situation(local.id, clock))

    assert incident.status is IncidentStatus.DETECTED
    assert confirmed == []
    assert await module.evidence.load(incident.id) == b"jpeg"


async def test_only_operator_confirmation_authorizes_the_alert(module, local, clock, confirmed):
    incident = await module.record_situation.execute(situation(local.id, clock))

    result = await module.confirm.execute(incident.id, OPERATOR)

    assert result.status is IncidentStatus.CONFIRMED
    assert [event.confirmed_by for event in confirmed] == [OPERATOR]


async def test_discarding_never_authorizes_the_alert(module, local, clock, confirmed):
    incident = await module.record_situation.execute(situation(local.id, clock))

    await module.discard.execute(incident.id, OPERATOR)

    assert confirmed == []
    with pytest.raises(ConflictError):
        await module.confirm.execute(incident.id, OPERATOR)


async def test_confirmation_requires_a_registered_number(module, establishments, clock, confirmed):
    local = await establishments.create.execute("Sin número", "Calle 2")
    incident = await module.record_situation.execute(situation(local.id, clock))

    with pytest.raises(ConflictError, match="WhatsApp del CAI"):
        await module.confirm.execute(incident.id, OPERATOR)

    assert confirmed == []
    assert (await module.get.execute(incident.id)).status is IncidentStatus.DETECTED


async def test_confirming_twice_sends_a_single_authorization(module, local, clock, confirmed):
    incident = await module.record_situation.execute(situation(local.id, clock))
    await module.confirm.execute(incident.id, OPERATOR)

    with pytest.raises(ConflictError):
        await module.confirm.execute(incident.id, "otro@example.com")

    assert len(confirmed) == 1


async def test_simultaneous_confirmations_authorize_only_once(module, local, clock, confirmed):
    incident = await module.record_situation.execute(situation(local.id, clock))
    results = await asyncio.gather(
        module.confirm.execute(incident.id, OPERATOR),
        module.confirm.execute(incident.id, "otro@example.com"),
        return_exceptions=True,
    )

    assert sum(isinstance(result, Incident) for result in results) == 1
    assert len(confirmed) == 1


async def test_audit_records_who_did_what(module, local, clock):
    incident = await module.record_situation.execute(situation(local.id, clock))
    clock.advance(minutes=1)
    await module.confirm.execute(incident.id, OPERATOR)
    await module.record_delivery.delivered(incident.id)

    saved = await module.get.execute(incident.id)

    assert [(a.status, a.actor) for a in saved.audit] == [
        (IncidentStatus.DETECTED, "sistema"),
        (IncidentStatus.CONFIRMED, OPERATOR),
        (IncidentStatus.NOTIFIED, "sistema"),
    ]


async def test_failed_delivery_can_be_retried_by_confirming_again(module, local, clock, confirmed):
    incident = await module.record_situation.execute(situation(local.id, clock))
    await module.confirm.execute(incident.id, OPERATOR)
    await module.record_delivery.failed(incident.id)

    await module.confirm.execute(incident.id, OPERATOR)

    assert len(confirmed) == 2


async def test_changes_are_published_for_live_clients(module, local, clock, bus):
    changes: list[IncidentStatus] = []

    async def record(event: IncidentChanged) -> None:
        changes.append(event.incident.status)

    bus.subscribe(IncidentChanged, record)

    incident = await module.record_situation.execute(situation(local.id, clock))
    await module.discard.execute(incident.id, OPERATOR)

    assert changes == [IncidentStatus.DETECTED, IncidentStatus.DISCARDED]


async def test_recent_incidents_are_listed_newest_first(module, local, clock):
    first = await module.record_situation.execute(situation(local.id, clock))
    clock.advance(minutes=1)
    second = await module.record_situation.execute(situation(local.id, clock))

    listed = await module.list_recent.execute(local.id)

    assert [incident.id for incident in listed] == [second.id, first.id]
