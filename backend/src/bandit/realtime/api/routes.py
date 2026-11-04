"""WebSocket de eventos: una conexión por navegador gracias al SharedWorker."""

import contextlib
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from bandit.identity.public import authenticate_websocket
from bandit.realtime.application.event_hub import EventHub, Message
from bandit.shared.errors import DomainError, PermissionDeniedError
from bandit.shared.ws import pump

router = APIRouter()


@router.websocket("/ws/events/{establishment_id}")
async def events(websocket: WebSocket, establishment_id: UUID) -> None:
    hub: EventHub = websocket.app.state.event_hub
    try:
        user = await authenticate_websocket(websocket)
        if not user.can_access(establishment_id):
            raise PermissionDeniedError("No tienes acceso a este local")
    except DomainError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    subscription = hub.subscribe(establishment_id)

    async def send(message: Message) -> None:
        await websocket.send_json(message)

    try:
        # Cada conexión nueva pide resincronizar, por si perdió eventos.
        await websocket.send_json({"type": "sync"})
        await pump(websocket, subscription, send)
    finally:
        hub.unsubscribe(establishment_id, subscription)
        with contextlib.suppress(WebSocketDisconnect, RuntimeError):
            await websocket.close()
