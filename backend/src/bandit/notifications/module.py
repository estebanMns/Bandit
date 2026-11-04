"""Composición del módulo de notificaciones."""

from bandit.establishments.public import GetEstablishment
from bandit.notifications.application.use_cases import (
    DeliverConfirmedAlert,
    PushNewIncident,
    RegisterPushTarget,
    SendTestMessage,
)
from bandit.notifications.domain.ports import AlertSender, PushSender
from bandit.notifications.infrastructure.repositories import SqlPushTargetRepository
from bandit.shared.clock import Clock
from bandit.shared.db import SessionFactory
from bandit.shared.events import EventBus


class NotificationsModule:
    def __init__(
        self,
        sessions: SessionFactory,
        establishments: GetEstablishment,
        alert_sender: AlertSender,
        push_sender: PushSender,
        bus: EventBus,
        clock: Clock,
    ) -> None:
        targets = SqlPushTargetRepository(sessions)
        self.deliver_alert = DeliverConfirmedAlert(establishments, alert_sender, bus)
        self.send_test_message = SendTestMessage(establishments, alert_sender, clock)
        self.register_push_target = RegisterPushTarget(targets)
        self.push_new_incident = PushNewIncident(targets, push_sender)
