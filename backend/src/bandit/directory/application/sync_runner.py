"""Coordina las extracciones: una a la vez, registradas y sin bloquear a quien las pide."""

import asyncio
import logging
from datetime import timedelta
from uuid import uuid4

from bandit.directory.application.use_cases import ListWanted, SyncDirectory
from bandit.directory.domain.models import SyncRun, SyncTrigger
from bandit.directory.domain.ports import SyncRunRepository
from bandit.shared.clock import Clock
from bandit.shared.error_summary import describe_error
from bandit.shared.errors import ConflictError, RateLimitedError

logger = logging.getLogger(__name__)


class DirectorySyncRunner:
    def __init__(
        self,
        sync: SyncDirectory,
        runs: SyncRunRepository,
        records: ListWanted,
        clock: Clock,
        manual_gap: timedelta,
        stale_after: timedelta,
    ) -> None:
        self._sync = sync
        self._runs = runs
        self._records = records
        self._clock = clock
        self._manual_gap = manual_gap
        self._stale_after = stale_after
        self._busy = False
        self._tasks: set[asyncio.Task[SyncRun | None]] = set()

    @property
    def running(self) -> bool:
        return self._busy

    async def latest(self, limit: int = 5) -> list[SyncRun]:
        return await self._runs.latest(limit)

    async def run(self, trigger: SyncTrigger) -> SyncRun | None:
        """Corre ahora. Si ya hay una en curso, no hace nada."""
        if self._busy:
            return None
        self._busy = True
        return await self._execute(trigger)

    async def _execute(self, trigger: SyncTrigger) -> SyncRun:
        run = SyncRun(id=uuid4(), trigger=trigger, started_at=self._clock.now())
        try:
            await self._runs.save(run)
            report = await self._sync.execute()
            run.published, run.rejected, run.retired = (
                report.published,
                report.rejected,
                report.retired,
            )
            run.completed = report.completed
            run.pages_failed = report.pages_failed
            run.error = report.error
        except Exception as error:
            run.error = describe_error(error)
            logger.warning("La extracción falló: %s", run.error)
        finally:
            run.finished_at = self._clock.now()
            self._busy = False
        await self._runs.save(run)
        return run

    async def start_manual(self) -> None:
        if self._busy:
            raise ConflictError("Ya hay una extracción en curso")
        latest = await self._runs.latest(1)
        if latest and self._clock.now() - latest[0].started_at < self._manual_gap:
            minutes = int(self._manual_gap.total_seconds() // 60)
            raise RateLimitedError(f"Espera {minutes} minutos entre extracciones")
        self._spawn(SyncTrigger.MANUAL)

    async def start_if_stale(self) -> bool:
        """Al arrancar: extrae si nunca se hizo, si es vieja o si el directorio está vacío."""
        latest = await self._runs.latest(1)
        now = self._clock.now()
        if not latest:
            stale = True
        else:
            age = now - latest[0].started_at
            empty = not await self._records.execute()
            stale = age >= self._stale_after or (empty and age >= self._manual_gap)
        if stale and not self._busy:
            self._spawn(SyncTrigger.STARTUP)
        return stale

    def _spawn(self, trigger: SyncTrigger) -> None:
        self._busy = True
        task = asyncio.create_task(self._execute(trigger))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def stop(self) -> None:
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def wait(self) -> None:
        await asyncio.gather(*list(self._tasks), return_exceptions=True)
