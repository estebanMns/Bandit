"""Bombeo de una suscripción hacia un WebSocket."""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import WebSocket, WebSocketDisconnect

from bandit.shared.fanout import Subscription

T = TypeVar("T")


async def pump(
    websocket: WebSocket, subscription: Subscription[T], send: Callable[[T], Awaitable[None]]
) -> None:
    """Envía hasta que el cliente se vaya o la suscripción se cierre."""

    async def forward() -> None:
        async for item in subscription:
            await send(item)

    async def watch_client() -> None:
        with contextlib.suppress(WebSocketDisconnect):
            while True:
                await websocket.receive()

    tasks = {asyncio.create_task(forward()), asyncio.create_task(watch_client())}
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    for task in done:
        with contextlib.suppress(WebSocketDisconnect, RuntimeError):
            task.result()
