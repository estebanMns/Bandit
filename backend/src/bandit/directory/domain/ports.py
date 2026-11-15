"""Puertos del módulo de directorio."""

from typing import Protocol

from bandit.directory.domain.models import ExtractedRecord, SyncRun, WantedRecord


class WantedRepository(Protocol):
    async def list_active(self) -> list[WantedRecord]: ...

    async def get_active(self, slug: str) -> WantedRecord | None: ...

    async def upsert(self, record: WantedRecord) -> None: ...

    async def delete(self, slug: str) -> None: ...


class SyncRunRepository(Protocol):
    async def save(self, run: SyncRun) -> None: ...

    async def latest(self, limit: int) -> list[SyncRun]: ...


class PageFetcher(Protocol):
    """Solo descarga URLs permitidas, respeta robots.txt y limita la velocidad."""

    async def fetch_text(self, url: str) -> str: ...

    async def fetch_bytes(self, url: str, max_bytes: int) -> bytes: ...


class MediaStore(Protocol):
    async def save(self, name: str, data: bytes, source: str | None = None) -> None:
        """Guarda el archivo; `source` es la URL de donde se descargó, si la hay."""
        ...

    async def source_of(self, name: str) -> str | None:
        """URL de origen del archivo guardado, o None si no existe o no se sabe."""
        ...

    async def delete(self, name: str) -> None: ...

    async def load(self, name: str) -> bytes | None:
        """Contenido del archivo, o None si no existe o el nombre no es válido."""
        ...


class SiteRevalidator(Protocol):
    async def revalidate(self) -> None: ...


class AgentTools(Protocol):
    """Lo único que el agente puede hacer. Cada acción se valida en código."""

    async def open_listing_page(self, page: int) -> str: ...

    async def open_listing_html(self, page: int) -> str: ...

    @property
    def known_flyers(self) -> frozenset[str]: ...

    def accepted_count(self) -> int: ...

    async def read_flyer(self, url: str) -> str: ...

    def submit_record(self, record: ExtractedRecord) -> str: ...

    def record_page_failure(self, detail: str) -> None: ...

    def finish(self) -> str: ...


class DirectoryAgent(Protocol):
    async def run(self, tools: AgentTools) -> None: ...
