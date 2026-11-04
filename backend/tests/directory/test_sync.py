import pytest

from bandit.directory.application.tools import SOURCE_URL
from bandit.directory.domain.models import ExtractedRecord
from bandit.directory.infrastructure.file_media import FileMediaStore
from bandit.directory.module import DirectoryModule
from bandit.shared.errors import NotFoundError

PHOTO = "https://www.policia.gov.co/sites/default/files/persona.jpg"


def page(*names: str) -> str:
    cards = "".join(f'<h3>{name}</h3><img src="{PHOTO}">' for name in names)
    return f"<main>{cards}</main>"


class FakeFetcher:
    def __init__(self, html):
        self.html = html

    async def fetch_text(self, url):
        return self.html

    async def fetch_bytes(self, url, max_bytes):
        return b"imagen"


class FakeAgent:
    def __init__(self, names, finish=True):
        self.names = names
        self.finish = finish

    async def run(self, tools):
        await tools.open_listing_page(0)
        for name in self.names:
            tools.submit_record(
                ExtractedRecord(name, None, None, None, None, None, (), PHOTO, None)
            )
        if self.finish:
            tools.finish()


class FakeRevalidator:
    def __init__(self):
        self.calls = 0

    async def revalidate(self):
        self.calls += 1


@pytest.fixture
def revalidator():
    return FakeRevalidator()


@pytest.fixture
def media(tmp_path):
    return FileMediaStore(str(tmp_path))


def build(sessions, clock, media, revalidator, names, published=None, finish=True):
    return DirectoryModule(
        sessions,
        FakeAgent(names, finish),
        FakeFetcher(page(*(published if published is not None else names))),
        media,
        revalidator,
        clock,
    )


async def test_publishes_records_and_their_photo(sessions, clock, media, revalidator):
    module = build(sessions, clock, media, revalidator, ["Ana Ejemplo"])

    report = await module.sync.execute()

    record = await module.get.execute("ana-ejemplo")
    assert report.published == 1
    assert record.source_url == SOURCE_URL
    assert media.path_of(record.photo_file) is not None
    assert revalidator.calls == 1


async def test_records_no_longer_listed_are_retired_with_their_files(
    sessions, clock, media, revalidator
):
    await build(sessions, clock, media, revalidator, ["Ana Ejemplo", "Beto Ejemplo"]).sync.execute()
    module = build(sessions, clock, media, revalidator, ["Ana Ejemplo"])

    report = await module.sync.execute()

    assert report.retired == 1
    with pytest.raises(NotFoundError):
        await module.get.execute("beto-ejemplo")
    assert media.path_of("beto-ejemplo.jpg") is None


async def test_incomplete_run_retires_nobody(sessions, clock, media, revalidator):
    await build(sessions, clock, media, revalidator, ["Ana Ejemplo"]).sync.execute()
    module = build(sessions, clock, media, revalidator, [], finish=False)

    report = await module.sync.execute()

    assert report.completed is False
    assert [record.slug for record in await module.list_active.execute()] == ["ana-ejemplo"]


async def test_finished_run_without_valid_records_retires_nobody(
    sessions, clock, media, revalidator
):
    await build(sessions, clock, media, revalidator, ["Ana Ejemplo"]).sync.execute()
    module = build(sessions, clock, media, revalidator, ["Inventado"], published=["Otro"])

    report = await module.sync.execute()

    assert report.completed is False
    assert report.rejected == 1
    assert len(await module.list_active.execute()) == 1


async def test_a_republished_person_becomes_visible_again(sessions, clock, media, revalidator):
    await build(sessions, clock, media, revalidator, ["Ana Ejemplo", "Beto"]).sync.execute()
    await build(sessions, clock, media, revalidator, ["Beto"]).sync.execute()
    module = build(sessions, clock, media, revalidator, ["Ana Ejemplo", "Beto"])

    await module.sync.execute()

    assert (await module.get.execute("ana-ejemplo")).active


def test_media_store_rejects_path_traversal(media):
    assert media.path_of("../secreto.txt") is None
    assert media.path_of("..\\secreto.txt") is None
