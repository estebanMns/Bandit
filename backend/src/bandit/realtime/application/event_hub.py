"""Difusión de eventos a todos los clientes conectados de un local."""

from collections import defaultdict
from typing import Any
from uuid import UUID

from bandit.shared.fanout import Overflow, Subscription, Topic

_QUEUE_CAPACITY = 64

Message = dict[str, Any]


class EventHub:
    """Un cliente muy lento se desconecta: al reconectar pide el estado actualizado."""

    def __init__(self) -> None:
        self._topics: dict[UUID, Topic[Message]] = defaultdict(
            lambda: Topic(_QUEUE_CAPACITY, Overflow.DISCONNECT)
        )

    def publish(self, establishment_id: UUID, message: Message) -> None:
        self._topics[establishment_id].publish(message)

    def subscribe(self, establishment_id: UUID) -> Subscription[Message]:
        return self._topics[establishment_id].subscribe()

    def unsubscribe(self, establishment_id: UUID, subscription: Subscription[Message]) -> None:
        self._topics[establishment_id].unsubscribe(subscription)
