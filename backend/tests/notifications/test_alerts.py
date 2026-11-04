from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
import respx

from bandit.establishments.module import EstablishmentsModule
from bandit.incidents.public import Incident, IncidentChanged, IncidentConfirmed
from bandit.notifications.application.use_cases import DeliverConfirmedAlert
from bandit.notifications.domain.models import (
    AlertDelivered,
    AlertFailed,
    AlertMessage,
    PushTarget,
    PushTargetGoneError,
)
from bandit.notifications.infrastructure.whatsapp_cloud import WhatsAppCloudSender
from bandit.notifications.module import NotificationsModule
from bandit.shared.errors import ConflictError
from bandit.shared.events import InMemoryEventBus

NUMBER = "+573001234567"
GRAPH_URL = "https://graph.facebook.com/v23.0/123/messages"


class FakeSender:
    def __init__(self, failures=0):
        self.failures = failures
        self.sent: list[tuple[str, AlertMessage]] = []

    async def send(self, to, message):
        if self.failures:
            self.failures -= 1
            raise RuntimeError("caído")
        self.sent.append((to, message))


class FakePush:
    def __init__(self, gone=False):
        self.gone = gone
        self.sent = []

    async def send(self, target, title, body, url):
        if self.gone:
            raise PushTargetGoneError
        self.sent.append((target.endpoint, title, url))


@pytest.fixture
def bus():
    return InMemoryEventBus()


@pytest.fixture
def results(bus):
    events = []

    async def record(event):
        events.append(event)

    bus.subscribe(AlertDelivered, record)
    bus.subscribe(AlertFailed, record)
    return events


@pytest.fixture
async def local(sessions):
    module = EstablishmentsModule(sessions)
    created = await module.create.execute("Bar La Esquina", "Calle 10 # 5-20")
    return await module.set_cai_whatsapp.execute(created.id, NUMBER)


def incident(establishment_id) -> Incident:
    return Incident(
        id=uuid4(),
        establishment_id=establishment_id,
        camera_id=uuid4(),
        camera_name="Barra",
        type="robbery",
        severity="high",
        confidence=0.9,
        description="Una persona amenaza al cajero.",
        detected_at=datetime(2026, 11, 5, 3, 30, tzinfo=UTC),
    )


def deliver(sessions, sender, bus):
    establishments = EstablishmentsModule(sessions)
    return DeliverConfirmedAlert(establishments.get, sender, bus, retry_delays=(0, 0))


async def test_sends_the_alert_with_local_time_and_no_identity(sessions, bus, results, local):
    sender = FakeSender()
    event = IncidentConfirmed(incident=incident(local.id), confirmed_by="ana@example.com")

    await deliver(sessions, sender, bus).execute(event)

    to, message = sender.sent[0]
    assert to == NUMBER
    assert message == AlertMessage(
        establishment="Bar La Esquina",
        address="Calle 10 # 5-20",
        situation="Atraco o hurto",
        time="04/11/2026 22:30",
        description="Una persona amenaza al cajero.",
    )
    assert isinstance(results[0], AlertDelivered)


async def test_retries_before_reporting_success(sessions, bus, results, local):
    sender = FakeSender(failures=2)

    await deliver(sessions, sender, bus).execute(
        IncidentConfirmed(incident=incident(local.id), confirmed_by="ana@example.com")
    )

    assert len(sender.sent) == 1
    assert isinstance(results[0], AlertDelivered)


async def test_reports_failure_after_exhausting_retries(sessions, bus, results, local):
    sender = FakeSender(failures=3)

    await deliver(sessions, sender, bus).execute(
        IncidentConfirmed(incident=incident(local.id), confirmed_by="ana@example.com")
    )

    assert sender.sent == []
    assert isinstance(results[0], AlertFailed)


async def test_detection_alone_never_reaches_whatsapp(sessions, bus, local, clock):
    """Solo `IncidentConfirmed` está conectado al envío: un cambio de estado no basta."""
    sender = FakeSender()
    module = NotificationsModule(
        sessions, EstablishmentsModule(sessions).get, sender, FakePush(), bus, clock
    )
    bus.subscribe(IncidentChanged, module.push_new_incident.execute)
    bus.subscribe(IncidentConfirmed, module.deliver_alert.execute)

    await bus.publish(IncidentChanged(incident=incident(local.id)))

    assert sender.sent == []


async def test_test_message_requires_a_saved_number(sessions, bus, clock):
    establishments = EstablishmentsModule(sessions)
    created = await establishments.create.execute("Sin número", "Calle 2")
    module = NotificationsModule(sessions, establishments.get, FakeSender(), FakePush(), bus, clock)

    with pytest.raises(ConflictError):
        await module.send_test_message.execute(created.id)


async def test_test_message_says_there_is_no_emergency(sessions, bus, clock, local):
    sender = FakeSender()
    module = NotificationsModule(
        sessions, EstablishmentsModule(sessions).get, sender, FakePush(), bus, clock
    )

    await module.send_test_message.execute(local.id)

    assert "No hay ninguna emergencia" in sender.sent[0][1].description


async def test_new_incident_pushes_to_operators_and_drops_dead_targets(sessions, bus, clock, local):
    push = FakePush()
    module = NotificationsModule(
        sessions, EstablishmentsModule(sessions).get, FakeSender(), push, bus, clock
    )
    target = PushTarget("https://push.example/1", "clave", "auth")
    await module.register_push_target.execute(local.id, target)
    new = incident(local.id)

    await module.push_new_incident.execute(IncidentChanged(incident=new))
    assert push.sent == [(target.endpoint, "Atraco o hurto", f"/incidentes/{new.id}")]

    push.gone = True
    await module.push_new_incident.execute(IncidentChanged(incident=replace(new)))
    push.gone = False
    push.sent.clear()
    await module.push_new_incident.execute(IncidentChanged(incident=new))
    assert push.sent == []


@respx.mock
async def test_whatsapp_adapter_sends_the_approved_template():
    route = respx.post(GRAPH_URL).mock(return_value=httpx.Response(200, json={"messages": []}))
    sender = WhatsAppCloudSender("token", "123", "bandit_incidente", "es", "v23.0")

    await sender.send(NUMBER, AlertMessage("Bar", "Calle 1", "Pelea", "22:30", "Pelea en la barra"))

    request = route.calls[0].request
    assert request.headers["authorization"] == "Bearer token"
    body = httpx.Response(200, content=request.content).json()
    assert body["to"] == "573001234567"
    assert body["template"]["name"] == "bandit_incidente"
    assert len(body["template"]["components"][0]["parameters"]) == 5


@respx.mock
async def test_whatsapp_adapter_raises_when_rejected():
    respx.post(GRAPH_URL).mock(return_value=httpx.Response(400))
    sender = WhatsAppCloudSender("token", "123", "bandit_incidente", "es", "v23.0")

    with pytest.raises(httpx.HTTPStatusError):
        await sender.send(NUMBER, AlertMessage("Bar", "Calle 1", "Pelea", "22:30", "Pelea"))


async def test_whatsapp_adapter_fails_clearly_without_configuration():
    sender = WhatsAppCloudSender("", "123", "bandit_incidente", "es", "v23.0")

    with pytest.raises(RuntimeError, match="no está configurado"):
        await sender.send(NUMBER, AlertMessage("Bar", "Calle 1", "Pelea", "22:30", "Pelea"))
