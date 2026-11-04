"""Composición del módulo de directorio."""

from bandit.directory.application.use_cases import GetWanted, ListWanted, SyncDirectory
from bandit.directory.domain.ports import (
    DirectoryAgent,
    MediaStore,
    PageFetcher,
    SiteRevalidator,
)
from bandit.directory.infrastructure.pdf_text import read_pdf_text
from bandit.directory.infrastructure.repositories import SqlWantedRepository
from bandit.shared.clock import Clock
from bandit.shared.db import SessionFactory


class DirectoryModule:
    def __init__(
        self,
        sessions: SessionFactory,
        agent: DirectoryAgent,
        fetcher: PageFetcher,
        media: MediaStore,
        revalidator: SiteRevalidator,
        clock: Clock,
    ) -> None:
        repository = SqlWantedRepository(sessions)
        self.media = media
        self.list_active = ListWanted(repository)
        self.get = GetWanted(repository)
        self.sync = SyncDirectory(
            agent, fetcher, read_pdf_text, repository, media, revalidator, clock
        )
