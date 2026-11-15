"""Lectura directa del listado de la Policía y fotos guardadas en la base."""

from datetime import timedelta

from bandit.directory.application.police_listing import (
    FallbackDirectoryAgent,
    HtmlDirectoryAgent,
    crime_in,
    parse_listing,
    region_in,
)
from bandit.directory.application.tools import SOURCE_URL, ScrapingTools
from bandit.directory.domain.models import SyncTrigger
from bandit.directory.infrastructure.db_media import DbMediaStore
from bandit.directory.module import DirectoryModule
from bandit.tools.upload_media import copy_directory_files

BASE = "https://www.policia.gov.co"


def card(name: str, photo: str, reward: str = "Hasta $10 millones de pesos en RECOMPENSA") -> str:
    """Misma estructura que publica la Policía; las personas son inventadas."""
    return f"""
    <li class="grid"><div class="buscado">
      <div class="recompensa"><h2>RECOMPENSA</h2><p>{reward}</p>
        <img src="/sites/default/files/{photo}.jpg" alt="{name}"></div>
      <div class="datos"><h2 class="nombre">{name}</h2>
        <p class="alias">Alias: No aplica</p>
        <p class="linea">L&Iacute;NEA DIRECTA</p>
        <p class="correo"><a href="mailto:unidad@policia.gov.co">unidad@policia.gov.co</a></p>
        <p class="telefono">3000000001 , 3000000002</p>
        <div class="file-link"><a href="/sites/default/files/{photo}.pdf">Ver Volante</a></div>
      </div></div></li>"""


def listing(*cards: str) -> str:
    return f"<html><body><main><ul>{''.join(cards)}</ul></main></body></html>"


FLYER = (
    "Gracias a usted, lo capturaremos POLICÍA METROPOLITANA DE CÚCUTA EL MÁS BUSCADO "
    "POR HOMICIDIO Hasta $10 millones"
)


class PagedFetcher:
    """Devuelve cada página del listado; las que no existen vienen vacías."""

    def __init__(self, pages: list[str], broken_page: int | None = None) -> None:
        self.pages = pages
        self.broken_page = broken_page
        self.downloads: list[str] = []

    async def fetch_text(self, url: str) -> str:
        page = int(url.rsplit("=", 1)[1])
        if page == self.broken_page:
            raise RuntimeError("caída")
        return self.pages[page] if page < len(self.pages) else listing()

    async def fetch_bytes(self, url: str, max_bytes: int) -> bytes:
        self.downloads.append(url)
        return b"%PDF volante" if url.endswith(".pdf") else b"imagen"


def flyer_text(_: bytes) -> str:
    return FLYER


def test_reads_every_field_of_a_card():
    [record] = parse_listing(listing(card("Ana Ejemplo Pérez", "ana")), SOURCE_URL, page=2)

    assert record.name == "Ana Ejemplo Pérez"
    assert record.alias == "No aplica"
    assert record.reward == "Hasta $10 millones de pesos en RECOMPENSA"
    assert record.photo_url == f"{BASE}/sites/default/files/ana.jpg"
    assert record.flyer_url == f"{BASE}/sites/default/files/ana.pdf"
    assert record.hotline_email == "unidad@policia.gov.co"
    assert record.hotline_phones == ("3000000001", "3000000002")
    assert record.listing_position == 2_000


def test_the_flyer_gives_the_unit_and_the_crime():
    assert region_in(FLYER) == "POLICÍA METROPOLITANA DE CÚCUTA"
    assert (
        region_in("DEPARTAMENTO DE POLICÍA VALLE EL MÁS BUSCADO") == "DEPARTAMENTO DE POLICÍA VALLE"
    )
    assert crime_in(FLYER) == "HOMICIDIO"
    assert crime_in("sin datos") is None


async def test_walks_every_page_and_finishes():
    fetcher = PagedFetcher(
        [
            listing(card("Ana Ejemplo", "ana"), card("Beto Ejemplo", "beto")),
            listing(card("Ceci", "ceci")),
        ]
    )
    tools = ScrapingTools(fetcher, flyer_text)

    await HtmlDirectoryAgent().run(tools)

    assert tools.finished
    assert sorted(record.name for record in tools.accepted.values()) == [
        "Ana Ejemplo",
        "Beto Ejemplo",
        "Ceci",
    ]
    ana = tools.accepted["ana ejemplo"]
    assert (ana.crime, ana.region) == ("HOMICIDIO", "POLICÍA METROPOLITANA DE CÚCUTA")
    assert tools.accepted["ceci"].listing_position == 1_000


async def test_a_broken_page_leaves_the_run_unfinished():
    fetcher = PagedFetcher([listing(card("Ana Ejemplo", "ana")), listing(card("Beto", "beto"))], 1)
    tools = ScrapingTools(fetcher, flyer_text)

    await HtmlDirectoryAgent().run(tools)

    assert not tools.finished
    assert tools.failed_pages == 1
    assert list(tools.accepted) == ["ana ejemplo"]


async def test_a_known_flyer_is_not_read_again():
    fetcher = PagedFetcher([listing(card("Ana Ejemplo", "ana"))])
    tools = ScrapingTools(fetcher, flyer_text, frozenset({f"{BASE}/sites/default/files/ana.pdf"}))

    await HtmlDirectoryAgent().run(tools)

    assert fetcher.downloads == []
    assert tools.accepted["ana ejemplo"].crime is None


class CountingAgent:
    def __init__(self) -> None:
        self.calls = 0

    async def run(self, tools) -> None:
        self.calls += 1


async def test_the_ai_only_helps_when_the_page_changed_and_once_a_day():
    now = [0.0]
    backup = CountingAgent()
    agent = FallbackDirectoryAgent(
        HtmlDirectoryAgent(), backup, gap_seconds=100, clock=lambda: now[0]
    )
    empty = PagedFetcher([listing()])

    await agent.run(ScrapingTools(empty, flyer_text))
    await agent.run(ScrapingTools(empty, flyer_text))
    now[0] = 150
    await agent.run(ScrapingTools(empty, flyer_text))
    await agent.run(ScrapingTools(PagedFetcher([listing(card("Ana", "ana"))]), flyer_text))

    assert backup.calls == 2


async def test_files_live_in_the_database(sessions):
    media = DbMediaStore(sessions)

    await media.save("ana.jpg", b"imagen", "https://origen/ana.jpg")

    assert await media.load("ana.jpg") == b"imagen"
    assert await media.source_of("ana.jpg") == "https://origen/ana.jpg"
    await media.delete("ana.jpg")
    assert await media.load("ana.jpg") is None
    assert await media.load("../secreto.jpg") is None


class Revalidator:
    async def revalidate(self) -> None:
        return None


def build(sessions, clock, fetcher) -> DirectoryModule:
    return DirectoryModule(
        sessions,
        HtmlDirectoryAgent(),
        fetcher,
        DbMediaStore(sessions),
        Revalidator(),
        clock,
        timedelta(minutes=10),
    )


async def test_every_ten_minutes_only_new_photos_are_downloaded(sessions, clock):
    fetcher = PagedFetcher([listing(card("Ana Ejemplo", "ana"))])
    module = build(sessions, clock, fetcher)

    await module.sync.execute()
    first = list(fetcher.downloads)
    await module.sync.execute()

    # La primera vez: el volante se lee, y la foto y el volante se guardan.
    assert sorted(first) == [
        f"{BASE}/sites/default/files/ana.jpg",
        f"{BASE}/sites/default/files/ana.pdf",
        f"{BASE}/sites/default/files/ana.pdf",
    ]
    assert fetcher.downloads == first
    record = await module.get.execute("ana-ejemplo")
    assert await module.media.load(record.photo_file) == b"imagen"


async def test_who_leaves_the_listing_is_deleted_with_the_photo(sessions, clock):
    fetcher = PagedFetcher([listing(card("Ana Ejemplo", "ana"), card("Beto Ejemplo", "beto"))])
    module = build(sessions, clock, fetcher)
    await module.sync.execute()

    fetcher.pages = [listing(card("Ana Ejemplo", "ana"))]
    report = await module.sync.execute()

    assert report.retired == 1
    assert [record.slug for record in await module.list_active.execute()] == ["ana-ejemplo"]
    assert await module.media.load("beto-ejemplo.jpg") is None


async def test_nobody_is_deleted_if_the_page_suddenly_lost_most_people(sessions, clock):
    names = ["Ana", "Beto", "Ceci", "Dario", "Elsa"]
    fetcher = PagedFetcher([listing(*(card(name, name.lower()) for name in names))])
    module = build(sessions, clock, fetcher)
    await module.sync.execute()

    fetcher.pages = [listing(card("Ana", "ana"))]
    report = await module.sync.execute()

    assert report.retired == 0
    assert report.error is not None
    assert len(await module.list_active.execute()) == 5


async def test_the_scheduled_job_skips_when_another_backend_just_ran(sessions, clock):
    module = build(sessions, clock, PagedFetcher([listing(card("Ana", "ana"))]))
    await module.runner.run(SyncTrigger.SCHEDULED)

    clock.advance(minutes=5)
    assert await module.runner.start_if_stale(SyncTrigger.SCHEDULED) is False
    clock.advance(minutes=4, seconds=30)
    assert await module.runner.start_if_stale(SyncTrigger.SCHEDULED) is True
    await module.runner.wait()
    latest = await module.runner.latest()
    assert latest[0].trigger == SyncTrigger.SCHEDULED


async def test_photos_from_this_pc_are_copied_to_the_database(sessions, tmp_path):
    folder = tmp_path / "directory"
    folder.mkdir()
    (folder / "ana.jpg").write_bytes(b"imagen")
    (folder / "notas.txt").write_text("no")
    media = DbMediaStore(sessions)

    assert await copy_directory_files(media, tmp_path) == (1, 0)
    assert await media.load("ana.jpg") == b"imagen"
