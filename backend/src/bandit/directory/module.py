"""Composición del módulo de directorio."""

from datetime import timedelta

from bandit.directory.application.sync_runner import DirectorySyncRunner
from bandit.directory.application.use_cases import GetWanted, ListWanted, SyncDirectory
from bandit.directory.domain.models import DEFAULT_SMLMV_COP
from bandit.directory.domain.ports import (
    DirectoryAgent,
    MediaStore,
    PageFetcher,
    SiteRevalidator,
)
from bandit.directory.infrastructure.pdf_text import read_pdf_text
from bandit.directory.infrastructure.repositories import (
    SqlSyncRunRepository,
    SqlWantedRepository,
)
from bandit.shared.clock import Clock
from bandit.shared.db import SessionFactory

# Una extracción manual cada media hora como máximo: cuida a la página de la Policía.
MANUAL_SYNC_GAP = timedelta(minutes=30)


class DirectoryModule:
    def __init__(
        self,
        sessions: SessionFactory,
        agent: DirectoryAgent,
        fetcher: PageFetcher,
        media: MediaStore,
        revalidator: SiteRevalidator,
        clock: Clock,
        sync_interval: timedelta,
        smlmv_cop: int = DEFAULT_SMLMV_COP,
    ) -> None:
        repository = SqlWantedRepository(sessions)
        self.media = media
        self.list_active = ListWanted(repository)
        self.get = GetWanted(repository)
        self.sync = SyncDirectory(
            agent, fetcher, read_pdf_text, repository, media, revalidator, clock, smlmv_cop
        )
        self.runner = DirectorySyncRunner(
            self.sync,
            SqlSyncRunRepository(sessions),
            self.list_active,
            clock,
            manual_gap=MANUAL_SYNC_GAP,
            stale_after=sync_interval,
        )
