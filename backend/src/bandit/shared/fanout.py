"""Fan-out en memoria: un publicador, N suscriptores con cola propia.

Cada suscriptor tiene su cola para que uno lento no frene a los demás. La
política de desborde decide qué pasa cuando esa cola se llena.
"""

import asyncio
from collections.abc import AsyncIterator
from enum import Enum
from typing import Generic, TypeVar

T = TypeVar("T")


class Overflow(Enum):
    DROP_OLDEST = "drop_oldest"
    """Para video: importa el fotograma más reciente."""

    DISCONNECT = "disconnect"
    """Para alertas: nada se pierde en silencio; el cliente reconecta y resincroniza."""


class Subscription(Generic[T]):
    def __init__(self, capacity: int, overflow: Overflow) -> None:
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=capacity)
        self._overflow = overflow
        self._closed = asyncio.Event()

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    def offer(self, item: T) -> None:
        if self.closed:
            return
        if self._queue.full():
            if self._overflow is Overflow.DISCONNECT:
                self.close()
                return
            self._queue.get_nowait()
        self._queue.put_nowait(item)

    def close(self) -> None:
        self._closed.set()

    async def __aiter__(self) -> AsyncIterator[T]:
        while True:
            if not self._queue.empty():
                yield self._queue.get_nowait()
                continue
            if self.closed:
                return
            getter = asyncio.ensure_future(self._queue.get())
            closer = asyncio.ensure_future(self._closed.wait())
            try:
                await asyncio.wait({getter, closer}, return_when=asyncio.FIRST_COMPLETED)
            finally:
                closer.cancel()
                if not getter.done():
                    getter.cancel()
            if getter.done() and not getter.cancelled():
                yield getter.result()


class Topic(Generic[T]):
    def __init__(self, capacity: int, overflow: Overflow) -> None:
        self._capacity = capacity
        self._overflow = overflow
        self._subscriptions: set[Subscription[T]] = set()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscriptions)

    def subscribe(self) -> Subscription[T]:
        subscription: Subscription[T] = Subscription(self._capacity, self._overflow)
        self._subscriptions.add(subscription)
        return subscription

    def unsubscribe(self, subscription: Subscription[T]) -> None:
        subscription.close()
        self._subscriptions.discard(subscription)

    def publish(self, item: T) -> None:
        for subscription in tuple(self._subscriptions):
            subscription.offer(item)
            if subscription.closed:
                self._subscriptions.discard(subscription)
