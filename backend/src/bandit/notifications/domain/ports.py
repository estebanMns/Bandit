"""Puertos del módulo de notificaciones."""

from typing import Protocol
from uuid import UUID

from bandit.notifications.domain.models import AlertMessage, PushTarget


class AlertSender(Protocol):
    async def send(self, to: str, message: AlertMessage) -> None:
        """Lanza una excepción si el proveedor no acepta el mensaje."""
        ...


class PushSender(Protocol):
    async def send(self, target: PushTarget, title: str, body: str, url: str) -> None: ...


class PushTargetRepository(Protocol):
    async def add(self, establishment_id: UUID, target: PushTarget) -> None: ...

    async def list_for(self, establishment_id: UUID) -> list[PushTarget]: ...

    async def remove(self, endpoint: str) -> None: ...
