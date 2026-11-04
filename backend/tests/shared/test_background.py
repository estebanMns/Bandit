import asyncio

from bandit.shared.background import BackgroundTasks


async def test_spawn_returns_before_the_work_finishes():
    tasks = BackgroundTasks()
    release = asyncio.Event()
    finished: list[bool] = []

    async def work() -> None:
        await release.wait()
        finished.append(True)

    tasks.spawn(work())
    assert finished == []

    release.set()
    await tasks.wait_all()
    assert finished == [True]


async def test_a_failing_task_does_not_break_the_others():
    tasks = BackgroundTasks()
    finished: list[bool] = []

    async def broken() -> None:
        raise RuntimeError("fallo")

    async def healthy() -> None:
        finished.append(True)

    tasks.spawn(broken())
    tasks.spawn(healthy())
    await tasks.wait_all()

    assert finished == [True]
