from dataclasses import dataclass

from bandit.shared.events import DomainEvent, InMemoryEventBus


@dataclass(frozen=True, slots=True, kw_only=True)
class Happened(DomainEvent):
    value: int


async def test_publish_fans_out_to_all_handlers():
    bus = InMemoryEventBus()
    received: list[str] = []

    async def first(event: Happened) -> None:
        received.append(f"first:{event.value}")

    async def second(event: Happened) -> None:
        received.append(f"second:{event.value}")

    bus.subscribe(Happened, first)
    bus.subscribe(Happened, second)

    await bus.publish(Happened(value=1))

    assert sorted(received) == ["first:1", "second:1"]


async def test_failing_handler_does_not_stop_the_others():
    bus = InMemoryEventBus()
    received: list[int] = []

    async def broken(event: Happened) -> None:
        raise RuntimeError("fallo")

    async def healthy(event: Happened) -> None:
        received.append(event.value)

    bus.subscribe(Happened, broken)
    bus.subscribe(Happened, healthy)

    await bus.publish(Happened(value=7))

    assert received == [7]
