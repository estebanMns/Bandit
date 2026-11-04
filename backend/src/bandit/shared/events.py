"""Bus de eventos entre módulos, con fan-out a todos los manejadores."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Hecho ocurrido en un módulo. Es inmutable."""


E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[E], Awaitable[None]]


class EventBus(Protocol):
    def subscribe(self, event_type: type[E], handler: Handler[E]) -> None: ...

    async def publish(self, event: DomainEvent) -> None: ...


class InMemoryEventBus:
    """Publica en paralelo; el fallo de un manejador no afecta a los demás."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler[Any]]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: Handler[E]) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        handlers = self._handlers[type(event)]
        results = await asyncio.gather(
            *(handler(event) for handler in handlers), return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error("Falló un manejador de %s", type(event).__name__, exc_info=result)
