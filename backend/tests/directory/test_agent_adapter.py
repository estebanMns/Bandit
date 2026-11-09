"""El agente pagina en código y llama una vez por página; una página fallida no tumba todo."""

from types import SimpleNamespace

from bandit.directory.domain.models import ExtractedRecord
from bandit.directory.infrastructure.gemini_agent import (
    GeminiDirectoryAgent,
    _PageRecords,
    build_prompt,
    page_links,
    position_of,
    record_from_arguments,
)
from bandit.directory.infrastructure.pdf_text import read_pdf_text

BASE = "https://www.policia.gov.co/sites/default/files"


def listing(*names: str) -> str:
    return " ".join(
        f"{name} [img: {BASE}/{name}.jpg] [a: {BASE}/{name}-volante.pdf]" for name in names
    )


class FakeTools:
    def __init__(self, pages: dict[int, str]):
        self.pages = pages
        self.opened: list[int] = []
        self.flyers: list[str] = []
        self.records: list[ExtractedRecord] = []
        self.failures: list[str] = []
        self.finished = False

    async def open_listing_page(self, page):
        self.opened.append(page)
        return self.pages.get(page, "Sin resultados")

    async def read_flyer(self, url):
        self.flyers.append(url)
        return f"Delito: HOMICIDIO ({url})"

    def submit_record(self, record):
        self.records.append(record)
        return "ok"

    def record_page_failure(self, detail):
        self.failures.append(detail)

    def finish(self):
        self.finished = True
        return "fin"


class FakeModels:
    """Responde por página con los nombres que encuentre en el prompt."""

    def __init__(self, fail_on_page: int | None = None):
        self.prompts: list[str] = []
        self.fail_on_page = fail_on_page

    async def generate_content(self, model, contents, config):
        self.prompts.append(contents)
        page = int(contents.split()[1])
        if page == self.fail_on_page:
            raise RuntimeError("503 UNAVAILABLE")
        names = [line.split()[0] for line in contents.splitlines()[1:2]]
        records = [
            {"name": name, "photo_url": f"{BASE}/{name}.jpg", "reward": "10 millones"}
            for name in names[0].split(" ")
            if name
        ]
        parsed = _PageRecords.model_validate({"records": records})
        return SimpleNamespace(parsed=parsed, text=None)


def agent_with(models: FakeModels) -> GeminiDirectoryAgent:
    agent = GeminiDirectoryAgent("clave-de-prueba", "modelo")
    agent._client = SimpleNamespace(aio=SimpleNamespace(models=models))  # type: ignore[assignment]
    return agent


async def test_pages_until_a_page_brings_nothing_new():
    tools = FakeTools({0: listing("Ana"), 1: listing("Beto"), 2: listing("Beto")})
    models = FakeModels()

    await agent_with(models).run(tools)

    assert tools.opened == [0, 1, 2]
    assert len(models.prompts) == 2
    assert [record.name for record in tools.records] == ["Ana", "Beto"]
    assert tools.finished


async def test_each_call_carries_only_its_page_and_flyers():
    tools = FakeTools({0: listing("Ana"), 1: listing("Beto")})
    models = FakeModels()

    await agent_with(models).run(tools)

    assert "Ana" in models.prompts[0] and "Beto" not in models.prompts[0]
    assert "Beto" in models.prompts[1] and "Ana" not in models.prompts[1]
    assert f"VOLANTE {BASE}/Beto-volante.pdf" in models.prompts[1]


async def test_a_failed_page_is_recorded_and_the_rest_continues():
    tools = FakeTools({0: listing("Ana"), 1: listing("Beto"), 2: listing("Carla")})

    await agent_with(FakeModels(fail_on_page=1)).run(tools)

    assert [record.name for record in tools.records] == ["Ana", "Carla"]
    assert len(tools.failures) == 1 and "RuntimeError" in tools.failures[0]
    assert tools.finished


async def test_position_follows_the_police_page_order():
    tools = FakeTools({0: listing("Ana"), 1: listing("Beto")})

    await agent_with(FakeModels()).run(tools)

    assert [record.listing_position for record in tools.records] == [0, 1000]


def test_position_without_photo_goes_after_the_known_ones():
    record = record_from_arguments({"name": "Ana"})

    assert position_of(record, 2, [f"{BASE}/x.jpg"], 3) == 2503


def test_links_keep_order_without_repeats():
    text = f"[img: {BASE}/a.jpg] [a: {BASE}/a.pdf] [img: {BASE}/a.jpg]"

    assert page_links(text) == [f"{BASE}/a.jpg", f"{BASE}/a.pdf"]


def test_long_flyers_are_trimmed_in_the_prompt():
    prompt = build_prompt(0, "página", {"https://x/v.pdf": "a" * 10_000})

    assert len(prompt) < 4_200


def test_builds_a_record_from_model_arguments():
    record = record_from_arguments(
        {"name": "Ana", "alias": "", "hotline_phones": ["300", "301"], "crime": "Hurto"}
    )

    assert record == ExtractedRecord(
        "Ana", None, "Hurto", None, None, None, ("300", "301"), None, None
    )


def test_unreadable_pdf_returns_empty_text():
    assert read_pdf_text(b"no es un pdf") == ""
