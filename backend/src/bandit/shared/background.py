"""Trabajo que no debe bloquear la petición que lo originó."""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

logger = logging.getLogger(__name__)


class BackgroundTasks:
    """Conserva referencias a las tareas y permite esperarlas al apagar."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    def spawn(self, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(work)
        self._tasks.add(task)
        task.add_done_callback(self._finished)

    def _finished(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            logger.error("Falló una tarea en segundo plano", exc_info=task.exception())

    async def wait_all(self) -> None:
        await asyncio.gather(*self._tasks, return_exceptions=True)
