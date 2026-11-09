"""Herramientas del agente: acá se decide qué se acepta, no en el modelo."""

import logging
from collections.abc import Callable
from urllib.parse import urlsplit

from bandit.directory.application.page_digest import digest_html
from bandit.directory.domain.models import ExtractedRecord, normalize_text
from bandit.directory.domain.ports import PageFetcher

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.policia.gov.co/los-mas-buscados-colombia"
MAX_LISTING_PAGES = 30
MAX_FLYER_BYTES = 10 * 1024 * 1024

_NOT_AVAILABLE = {"n/a", "no aplica", ""}


def _meaningful(value: str | None) -> str | None:
    if value is None or normalize_text(value) in _NOT_AVAILABLE:
        return None
    return value.strip()


class ScrapingTools:
    def __init__(self, fetcher: PageFetcher, read_pdf_text: Callable[[bytes], str]) -> None:
        self._fetcher = fetcher
        self._read_pdf_text = read_pdf_text
        self._evidence: list[str] = []
        self._known_urls: set[str] = set()
        self._flyer_texts: dict[str, str] = {}
        self.accepted: dict[str, ExtractedRecord] = {}
        self.rejected = 0
        self.finished = False
        self.failed_pages = 0
        self.last_error: str | None = None

    async def open_listing_page(self, page: int) -> str:
        if not 0 <= page < MAX_LISTING_PAGES:
            return "Esa página está fuera del rango permitido."
        html = await self._fetcher.fetch_text(f"{SOURCE_URL}?page={page}")
        digest = digest_html(html, SOURCE_URL)
        self._evidence.append(normalize_text(digest.text))
        self._known_urls |= digest.urls
        return digest.text

    async def read_flyer(self, url: str) -> str:
        if url not in self._known_urls or not urlsplit(url).path.lower().endswith(".pdf"):
            return "Ese volante no aparece en las páginas abiertas."
        if url not in self._flyer_texts:
            pdf = await self._fetcher.fetch_bytes(url, MAX_FLYER_BYTES)
            self._flyer_texts[url] = self._read_pdf_text(pdf)
            self._evidence.append(normalize_text(self._flyer_texts[url]))
        return self._flyer_texts[url] or "El volante no tiene texto legible."

    def _is_backed_by_source(self, value: str) -> bool:
        needle = normalize_text(value)
        return any(needle in evidence for evidence in self._evidence)

    def _clean(self, record: ExtractedRecord) -> ExtractedRecord | None:
        """Rechaza lo que no esté escrito en la fuente: evita publicar datos inventados."""
        cleaned = ExtractedRecord(
            name=record.name.strip(),
            alias=_meaningful(record.alias),
            crime=_meaningful(record.crime),
            reward=_meaningful(record.reward),
            region=_meaningful(record.region),
            hotline_email=_meaningful(record.hotline_email),
            hotline_phones=tuple(phone for phone in record.hotline_phones if phone.strip()),
            photo_url=record.photo_url if record.photo_url in self._known_urls else None,
            flyer_url=record.flyer_url if record.flyer_url in self._known_urls else None,
            listing_position=record.listing_position,
        )
        claims = [
            cleaned.name,
            cleaned.alias,
            cleaned.crime,
            cleaned.reward,
            cleaned.region,
            *cleaned.hotline_phones,
        ]
        if not cleaned.name or not all(
            self._is_backed_by_source(claim) for claim in claims if claim is not None
        ):
            return None
        return cleaned

    def submit_record(self, record: ExtractedRecord) -> str:
        cleaned = self._clean(record)
        if cleaned is None:
            self.rejected += 1
            logger.warning("Se rechazó un registro sin respaldo textual en la fuente")
            return "Rechazado: algún dato no aparece textualmente en la fuente."
        self.accepted[normalize_text(cleaned.name)] = cleaned
        return "Registro aceptado."

    def record_page_failure(self, detail: str) -> None:
        """Una página que falló no detiene la extracción, pero impide retirar registros."""
        self.failed_pages += 1
        self.last_error = detail[:300]
        logger.warning("Falló la extracción de una página: %s", self.last_error)

    def finish(self) -> str:
        self.finished = True
        return "Extracción terminada."
