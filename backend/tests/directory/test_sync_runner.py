"""Las extracciones van de una en una, quedan registradas y no castigan a la página fuente."""

import asyncio

import pytest

from bandit.directory.domain.models import SyncTrigger
from bandit.directory.infrastructure.file_media import FileMediaStore
from bandit.shared.errors import ConflictError, RateLimitedError
from tests.directory.test_sync import FakeRevalidator, build


class SlowAgent:
    def __init__(self):
        self.release = asyncio.Event()
        self.calls = 0

    async def run(self, tools):
        self.calls += 1
        await self.release.wait()


class BrokenAgent:
    async def run(self, tools):
        raise RuntimeError("caída")


@pytest.fixture
def media(tmp_path):
    return FileMediaStore(str(tmp_path))


@pytest.fixture
def module(sessions, clock, media):
    return build(sessions, clock, media, FakeRevalidator(), ["Ana Ejemplo"])


async def test_each_run_is_recorded_with_its_result(module):
    run = await module.runner.run(SyncTrigger.SCHEDULED)

    [saved] = await module.runner.latest()
    assert saved.id == run.id
    assert (saved.published, saved.completed, saved.error) == (1, True, None)
    assert saved.finished_at is not None


async def test_failures_are_recorded_instead_of_raised(module):
    module.sync._agent = BrokenAgent()

    run = await module.runner.run(SyncTrigger.SCHEDULED)

    assert run.error == "RuntimeError"
    assert module.runner.running is False


async def test_only_one_extraction_runs_at_a_time(module):
    agent = SlowAgent()
    module.sync._agent = agent

    await module.runner.start_manual()
    with pytest.raises(ConflictError):
        await module.runner.start_manual()
    assert await module.runner.run(SyncTrigger.SCHEDULED) is None

    agent.release.set()
    await module.runner.wait()
    assert agent.calls == 1
    assert module.runner.running is False


async def test_manual_runs_wait_between_them(module, clock):
    await module.runner.start_manual()
    await module.runner.wait()

    with pytest.raises(RateLimitedError):
        await module.runner.start_manual()

    clock.advance(minutes=31)
    await module.runner.start_manual()
    await module.runner.wait()
    assert len(await module.runner.latest()) == 2


async def test_startup_extracts_only_when_needed(module, clock):
    assert await module.runner.start_if_stale() is True
    await module.runner.wait()

    assert await module.runner.start_if_stale() is False

    clock.advance(hours=24)
    assert await module.runner.start_if_stale() is True
    await module.runner.wait()


async def test_startup_retries_an_empty_directory(sessions, clock, media):
    module = build(sessions, clock, media, FakeRevalidator(), [], finish=False)
    await module.runner.run(SyncTrigger.STARTUP)

    assert await module.runner.start_if_stale() is False

    clock.advance(minutes=31)
    assert await module.runner.start_if_stale() is True
    await module.runner.wait()
