"""Las páginas fallidas se reintentan tras esperar y dejan de contar como perdidas."""

import json
from types import SimpleNamespace

from bandit.directory.infrastructure.gemini_agent import GeminiDirectoryAgent

PHOTO = "https://www.policia.gov.co/sites/default/files/persona.jpg"


class FakeModels:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    async def generate_content(self, model, contents, config):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        payload = {"records": [{"name": "Ana Ejemplo", "photo_url": PHOTO}]}
        return SimpleNamespace(parsed=None, text=json.dumps(payload))


class FakeClient:
    def __init__(self, failures: int) -> None:
        self.aio = SimpleNamespace(models=FakeModels(failures))


class FakeTools:
    def __init__(self) -> None:
        self.failed_pages = 0
        self.records: list = []
        self.finished = False

    async def open_listing_page(self, page: int) -> str:
        return f"Listado [img: {PHOTO}]" if page == 0 else "Sin más personas"

    async def read_flyer(self, url: str) -> str:
        return ""

    def submit_record(self, record) -> str:
        self.records.append(record)
        return "Registro aceptado."

    def record_page_failure(self, detail: str) -> None:
        self.failed_pages += 1

    def resolve_page_failure(self) -> None:
        self.failed_pages = max(0, self.failed_pages - 1)

    def finish(self) -> str:
        self.finished = True
        return "Extracción terminada."


class Sleeps:
    def __init__(self) -> None:
        self.durations: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.durations.append(seconds)


async def test_failed_page_is_retried_and_no_longer_counts_as_failed():
    sleeps = Sleeps()
    client = FakeClient(failures=1)
    agent = GeminiDirectoryAgent(
        "clave", "modelo", client=client, sleep=sleeps, retry_passes=2, retry_wait_seconds=90
    )
    tools = FakeTools()

    await agent.run(tools)

    assert tools.finished is True
    assert tools.failed_pages == 0
    assert len(tools.records) == 1
    assert sleeps.durations == [90]
    assert client.aio.models.calls == 2


async def test_page_that_keeps_failing_stays_counted_and_stops_after_passes():
    sleeps = Sleeps()
    client = FakeClient(failures=10)
    agent = GeminiDirectoryAgent(
        "clave", "modelo", client=client, sleep=sleeps, retry_passes=2, retry_wait_seconds=60
    )
    tools = FakeTools()

    await agent.run(tools)

    assert tools.finished is True
    assert tools.failed_pages == 1
    assert tools.records == []
    assert sleeps.durations == [60, 60]
    assert client.aio.models.calls == 3
