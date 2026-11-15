"""Lectura directa del listado de la Policía, sin IA.

La página publica cada persona en una tarjeta con la misma estructura (``div.buscado``): foto,
recompensa, nombre, alias, correo, teléfonos y volante en PDF. Leerla así es gratis, rápido y no
depende de la cuota de Gemini. Todo pasa igual por las herramientas, que rechazan cualquier dato
que no esté escrito en la fuente.
"""

import logging
import re
import time
from collections.abc import Callable
from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser, LexborNode

from bandit.directory.application.tools import MAX_LISTING_PAGES, SOURCE_URL
from bandit.directory.domain.models import ExtractedRecord, normalize_text
from bandit.directory.domain.ports import AgentTools, DirectoryAgent
from bandit.shared.error_summary import describe_error

logger = logging.getLogger(__name__)

# Orden de la página: la página N empieza en N * 1000, igual que el agente de Gemini.
_PAGE_STRIDE = 1_000
_ALIAS_PREFIX = re.compile(r"^\s*alias\s*:?\s*", re.IGNORECASE)
_PHONE_SPLIT = re.compile(r"\s*[,;/]\s*|\s+y\s+")
_REGION = re.compile(
    r"(POLIC[IÍ]A\s+METROPOLITANA\s+(?:DE\s+|DEL\s+)+[A-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ]+){0,4}"
    r"|DEPARTAMENTO\s+DE\s+POLIC[IÍ]A\s+[A-ZÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ]+){0,3})"
)
# Palabras que cortan la región: lo que sigue en el volante ya no es el nombre de la unidad.
_REGION_STOP = re.compile(r"\s+(?:EL|LOS|LA|HASTA|ALIAS|GRACIAS)\b.*$")
_CRIMES = (
    "FEMINICIDIO",
    "HOMICIDIO",
    "SECUESTRO",
    "EXTORSIÓN",
    "EXTORSION",
    "TERRORISMO",
    "ACCESO CARNAL",
    "DELITO SEXUAL",
    "NARCOTRÁFICO",
    "TRÁFICO DE ESTUPEFACIENTES",
    "CONCIERTO PARA DELINQUIR",
    "HURTO",
)


def _text(node: LexborNode | None) -> str | None:
    if node is None:
        return None
    value = " ".join(node.text(separator=" ", strip=True).split())
    return value or None


def _card(node: LexborNode, base_url: str, position: int) -> ExtractedRecord | None:
    name = _text(node.css_first(".nombre"))
    if not name:
        return None
    alias = _text(node.css_first(".alias"))
    alias = _ALIAS_PREFIX.sub("", alias) if alias else None
    reward = _text(node.css_first(".recompensa p"))
    image = node.css_first(".recompensa img") or node.css_first("img")
    photo = image.attributes.get("src") if image else None
    flyer_link = node.css_first(".file-link a")
    flyer = flyer_link.attributes.get("href") if flyer_link else None
    email = _text(node.css_first(".correo"))
    phones = _text(node.css_first(".telefono")) or ""
    return ExtractedRecord(
        name=name,
        alias=alias or None,
        crime=None,
        reward=reward,
        region=None,
        hotline_email=email,
        hotline_phones=tuple(phone for phone in _PHONE_SPLIT.split(phones) if phone),
        photo_url=urljoin(base_url, photo) if photo else None,
        flyer_url=urljoin(base_url, flyer) if flyer else None,
        listing_position=position,
    )


def parse_listing(html: str, base_url: str = SOURCE_URL, page: int = 0) -> list[ExtractedRecord]:
    """Las tarjetas de una página del listado, en el orden en que la Policía las publica."""
    tree = LexborHTMLParser(html)
    records = []
    for index, node in enumerate(tree.css("div.buscado")):
        record = _card(node, base_url, page * _PAGE_STRIDE + index)
        if record is not None:
            records.append(record)
    return records


def region_in(flyer: str) -> str | None:
    """La unidad de policía que publica el volante, tal como aparece escrita."""
    match = _REGION.search(flyer)
    if match is None:
        return None
    return _REGION_STOP.sub("", " ".join(match.group(1).split())) or None


def crime_in(flyer: str) -> str | None:
    """El primer delito conocido que aparece escrito en el volante."""
    upper = flyer.upper()
    for crime in _CRIMES:
        if crime in upper:
            return crime
    return None


class HtmlDirectoryAgent:
    """Recorre las páginas del listado y envía cada tarjeta a las herramientas."""

    async def run(self, tools: AgentTools) -> None:
        seen: set[str] = set()
        for page in range(MAX_LISTING_PAGES):
            try:
                html = await tools.open_listing_html(page)
            except Exception as error:
                # Sin terminar la corrida: así nunca se elimina a nadie por una página caída.
                tools.record_page_failure(f"página {page}: {describe_error(error)}")
                return
            cards = [
                card
                for card in parse_listing(html, SOURCE_URL, page)
                if normalize_text(card.name) not in seen
            ]
            if not cards:
                break
            for card in cards:
                seen.add(normalize_text(card.name))
                tools.submit_record(await self._with_flyer(tools, card))
        tools.finish()

    async def _with_flyer(self, tools: AgentTools, card: ExtractedRecord) -> ExtractedRecord:
        """Delito y unidad salen del volante, que solo se lee la primera vez que aparece."""
        if card.flyer_url is None or card.flyer_url in tools.known_flyers:
            return card
        try:
            flyer = await tools.read_flyer(card.flyer_url)
        except Exception as error:
            logger.warning("No se pudo leer un volante: %s", describe_error(error))
            return card
        return ExtractedRecord(
            name=card.name,
            alias=card.alias,
            crime=crime_in(flyer),
            reward=card.reward,
            region=region_in(flyer),
            hotline_email=card.hotline_email,
            hotline_phones=card.hotline_phones,
            photo_url=card.photo_url,
            flyer_url=card.flyer_url,
            listing_position=card.listing_position,
        )


# El respaldo con IA es caro: como mucho una vez al día.
BACKUP_GAP_SECONDS = 24 * 60 * 60


class FallbackDirectoryAgent:
    """Usa el lector directo y, solo si no encontró a nadie (la página cambió), la IA."""

    def __init__(
        self,
        primary: DirectoryAgent,
        backup: DirectoryAgent,
        gap_seconds: float = BACKUP_GAP_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._primary = primary
        self._backup = backup
        self._gap = gap_seconds
        self._clock = clock
        self._last_backup: float | None = None

    async def run(self, tools: AgentTools) -> None:
        await self._primary.run(tools)
        if tools.accepted_count() > 0:
            return
        now = self._clock()
        if self._last_backup is not None and now - self._last_backup < self._gap:
            logger.warning("El lector directo no encontró registros; la IA ya se usó hoy")
            return
        self._last_backup = now
        logger.warning("El lector directo no encontró registros; se intenta con la IA")
        await self._backup.run(tools)
