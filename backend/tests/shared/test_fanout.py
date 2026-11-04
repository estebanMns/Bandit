import asyncio

from bandit.shared.fanout import Overflow, Topic


async def collect(subscription, count):
    items = []
    async for item in subscription:
        items.append(item)
        if len(items) == count:
            break
    return items


async def test_every_subscriber_receives_each_item():
    topic: Topic[int] = Topic(capacity=4, overflow=Overflow.DROP_OLDEST)
    first, second = topic.subscribe(), topic.subscribe()

    topic.publish(1)
    topic.publish(2)

    assert await collect(first, 2) == [1, 2]
    assert await collect(second, 2) == [1, 2]


async def test_slow_video_subscriber_keeps_the_newest_items():
    topic: Topic[int] = Topic(capacity=2, overflow=Overflow.DROP_OLDEST)
    slow = topic.subscribe()

    for value in range(5):
        topic.publish(value)

    assert await collect(slow, 2) == [3, 4]


async def test_overflowing_alert_subscriber_is_disconnected_without_affecting_others():
    topic: Topic[int] = Topic(capacity=1, overflow=Overflow.DISCONNECT)
    slow, healthy = topic.subscribe(), topic.subscribe()

    topic.publish(1)
    assert await collect(healthy, 1) == [1]
    topic.publish(2)

    assert slow.closed
    assert topic.subscriber_count == 1


async def test_closing_ends_iteration():
    topic: Topic[int] = Topic(capacity=1, overflow=Overflow.DROP_OLDEST)
    subscription = topic.subscribe()
    task = asyncio.create_task(collect(subscription, 1))
    await asyncio.sleep(0)

    topic.unsubscribe(subscription)

    assert await asyncio.wait_for(task, 1) == []
