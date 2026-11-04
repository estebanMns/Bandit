from uuid import uuid4

from bandit.realtime.application.event_hub import EventHub


async def first(subscription):
    async for message in subscription:
        return message


async def test_messages_reach_every_client_of_the_establishment():
    hub = EventHub()
    local = uuid4()
    one, two = hub.subscribe(local), hub.subscribe(local)

    hub.publish(local, {"type": "incident"})

    assert await first(one) == {"type": "incident"}
    assert await first(two) == {"type": "incident"}


async def test_messages_do_not_leak_to_other_establishments():
    hub = EventHub()
    other = hub.subscribe(uuid4())

    hub.publish(uuid4(), {"type": "incident"})

    assert other._queue.empty()


async def test_slow_client_is_disconnected_instead_of_losing_alerts_silently():
    hub = EventHub()
    local = uuid4()
    slow = hub.subscribe(local)

    for _ in range(65):
        hub.publish(local, {"type": "incident"})

    assert slow.closed
