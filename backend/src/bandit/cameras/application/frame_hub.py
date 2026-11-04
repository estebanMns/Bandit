"""Fan-out de fotogramas: una captura por cámara, N consumidores."""

from collections import defaultdict
from uuid import UUID

from bandit.cameras.domain.models import Frame
from bandit.shared.fanout import Overflow, Subscription, Topic

_QUEUE_CAPACITY = 2


class FrameHub:
    """Cada consumidor retiene poco: siempre importa el fotograma más reciente."""

    def __init__(self) -> None:
        self._topics: dict[UUID, Topic[Frame]] = defaultdict(
            lambda: Topic(_QUEUE_CAPACITY, Overflow.DROP_OLDEST)
        )

    def publish(self, frame: Frame) -> None:
        self._topics[frame.camera_id].publish(frame)

    def subscribe(self, camera_id: UUID) -> Subscription[Frame]:
        return self._topics[camera_id].subscribe()

    def unsubscribe(self, camera_id: UUID, subscription: Subscription[Frame]) -> None:
        self._topics[camera_id].unsubscribe(subscription)
