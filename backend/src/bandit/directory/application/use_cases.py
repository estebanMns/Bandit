"""Casos de uso del directorio."""

import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from bandit.directory.application.tools import SOURCE_URL, ScrapingTools
from bandit.directory.domain.models import (
    ExtractedRecord,
    SyncReport,
    WantedRecord,
    parse_reward,
    priority_key,
    slugify,
)
from bandit.directory.domain.ports import (
    DirectoryAgent,
    MediaStore,
    PageFetcher,
    SiteRevalidator,
    WantedRepository,
)
from bandit.shared.clock import Clock
from bandit.shared.errors import NotFoundError

logger = logging.getLogger(__name__)

_MAX_PHOTO_BYTES = 5 * 1024 * 1024
_MAX_FLYER_BYTES = 10 * 1024 * 1024
_ALLOWED_PHOTO_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class ListWanted:
    def __init__(self, records: WantedRepository) -> None:
        self._records = records

    async def execute(self) -> list[WantedRecord]:
        """Primero la recompensa más alta, luego el delito más grave publicado."""
        return sorted(await self._records.list_active(), key=priority_key)


class GetWanted:
    def __init__(self, records: WantedRepository) -> None:
        self._records = records

    async def execute(self, slug: str) -> WantedRecord:
        record = await self._records.get_active(slug)
        if record is None:
            raise NotFoundError("El registro no existe o ya no está publicado")
        return record


class SyncDirectory:
    def __init__(
        self,
        agent: DirectoryAgent,
        fetcher: PageFetcher,
        read_pdf_text: Callable[[bytes], str],
        records: WantedRepository,
        media: MediaStore,
        revalidator: SiteRevalidator,
        clock: Clock,
    ) -> None:
        self._agent = agent
        self._fetcher = fetcher
        self._read_pdf_text = read_pdf_text
        self._records = records
        self._media = media
        self._revalidator = revalidator
        self._clock = clock

    async def execute(self) -> SyncReport:
        tools = ScrapingTools(self._fetcher, self._read_pdf_text)
        await self._agent.run(tools)
        complete = tools.finished and tools.failed_pages == 0
        if not tools.accepted:
            logger.warning("La extracción no aceptó registros; el directorio queda como estaba")
            return SyncReport(0, tools.rejected, 0, False, tools.failed_pages, tools.last_error)

        current = {record.slug: record for record in await self._records.list_active()}
        published: set[str] = set()
        for extracted in tools.accepted.values():
            record = await self._publish(extracted, current)
            published.add(record.slug)

        # Lo aceptado se publica siempre; solo una corrida completa retira a quien ya no está.
        retired = 0
        if complete:
            for slug, record in current.items():
                if slug not in published:
                    await self._retire(record)
                    retired += 1

        await self._revalidator.revalidate()
        return SyncReport(
            len(published), tools.rejected, retired, complete, tools.failed_pages, tools.last_error
        )

    async def _publish(
        self, extracted: ExtractedRecord, current: dict[str, WantedRecord]
    ) -> WantedRecord:
        slug = slugify(extracted.name)
        now = self._clock.now()
        existing = current.get(slug)
        record = WantedRecord(
            id=existing.id if existing else uuid4(),
            slug=slug,
            name=extracted.name,
            alias=extracted.alias,
            crime=extracted.crime,
            reward=extracted.reward,
            region=extracted.region,
            hotline_email=extracted.hotline_email,
            hotline_phones=list(extracted.hotline_phones),
            photo_file=existing.photo_file if existing else None,
            flyer_file=existing.flyer_file if existing else None,
            source_url=SOURCE_URL,
            first_seen_at=existing.first_seen_at if existing else now,
            last_seen_at=now,
            reward_amount=parse_reward(extracted.reward),
            listing_position=extracted.listing_position,
        )
        record.photo_file = await self._download(
            slug, extracted.photo_url, _MAX_PHOTO_BYTES, record.photo_file, photo=True
        )
        record.flyer_file = await self._download(
            slug, extracted.flyer_url, _MAX_FLYER_BYTES, record.flyer_file, photo=False
        )
        await self._records.upsert(record)
        return record

    async def _download(
        self, slug: str, url: str | None, limit: int, fallback: str | None, photo: bool
    ) -> str | None:
        if url is None:
            return fallback
        suffix = PurePosixPath(unquote(urlsplit(url).path)).suffix.lower()
        if photo and suffix not in _ALLOWED_PHOTO_SUFFIXES:
            return fallback
        name = f"{slug}{suffix}" if photo else f"{slug}-volante.pdf"
        try:
            await self._media.save(name, await self._fetcher.fetch_bytes(url, limit))
        except Exception as error:
            logger.warning("No se pudo descargar un archivo: %s", type(error).__name__)
            return fallback
        return name

    async def _retire(self, record: WantedRecord) -> None:
        for name in (record.photo_file, record.flyer_file):
            if name:
                await self._media.delete(name)
        await self._records.upsert(replace(record, active=False, photo_file=None, flyer_file=None))
