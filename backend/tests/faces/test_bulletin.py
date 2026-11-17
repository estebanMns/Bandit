"""Modo boletín: una consulta por imagen; la alerta queda como posible coincidencia."""

from uuid import uuid4

from bandit.cameras.public import Camera
from bandit.faces.application.watcher import AlertGate, CameraFaceWatch, FacePolicy
from bandit.faces.domain.models import (
    DailyLimit,
    FaceCheckDone,
    FaceOutcome,
    FaceVerdict,
    WatchedPerson,
)
from bandit.faces.infrastructure.bulletin_watch_list import BulletinWatchList
from bandit.shared.events import InMemoryEventBus
from tests.faces.test_watcher import START, Clock, Motion, People

PEOPLE = [WatchedPerson("Ana", (b"ana",)), WatchedPerson("Beto", (b"beto",))]
FOUND_BETO = FaceVerdict(True, True, 0.93, "Mismos rasgos.")


class BatchComparer:
    """Solo implementa identify: en modo boletín no se usa compare por persona."""

    def __init__(self, *results):
        self.results = list(results)
        self.calls = []

    async def compare(self, references, probe):  # pragma: no cover - no debe llamarse
        raise AssertionError("En modo boletín no se compara persona por persona")

    async def identify(self, candidates, probe):
        self.calls.append([person.name for person in candidates])
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def build(comparer, batched=True):
    bus = InMemoryEventBus()
    events = []

    async def collect(event: FaceCheckDone):
        events.append(event)

    bus.subscribe(FaceCheckDone, collect)
    watch = CameraFaceWatch(
        Camera(uuid4(), uuid4(), "Entrada", ""),
        comparer,
        People(PEOPLE),
        Motion(),
        DailyLimit(100, Clock()),
        bus,
        FacePolicy(min_interval_seconds=5, motion_threshold=0.02, batched=batched),
        AlertGate(600),
    )
    return watch, events


async def test_one_identify_call_per_frame_names_the_matched_candidate():
    comparer = BatchComparer((FOUND_BETO, 1))
    watch, events = build(comparer)

    await watch.on_frame(b"x", START)

    assert comparer.calls == [["Ana", "Beto"]]
    check = events[0].check
    assert check.outcome is FaceOutcome.MATCH
    assert check.person == "Beto"
    assert check.alerted


async def test_a_low_confidence_identification_is_not_an_alert():
    weak = FaceVerdict(True, True, 0.6, "Se parece.")
    watch, events = build(BatchComparer((weak, 0)))

    await watch.on_frame(b"x", START)

    assert events[0].check.outcome is FaceOutcome.NO_MATCH
    assert not events[0].check.alerted


async def test_no_candidate_is_reported_as_no_match():
    watch, events = build(BatchComparer((FaceVerdict(True, False, 0.9, "Otra."), None)))

    await watch.on_frame(b"x", START)

    assert events[0].check.outcome is FaceOutcome.NO_MATCH


async def test_a_failed_identify_call_is_reported_as_error():
    watch, events = build(BatchComparer(RuntimeError("cuota")))

    await watch.on_frame(b"x", START)

    assert events[0].check.outcome is FaceOutcome.ERROR
    assert not events[0].check.alerted


async def test_pruebas_mode_still_compares_one_person_at_a_time():
    class PerPerson:
        def __init__(self):
            self.compared = []

        async def compare(self, references, probe):
            self.compared.append(references)
            return FaceVerdict(True, False, 0.9, "No.")

        async def identify(self, candidates, probe):  # pragma: no cover
            raise AssertionError("El modo pruebas no usa identify")

    comparer = PerPerson()
    watch, _ = build(comparer, batched=False)

    await watch.on_frame(b"x", START)

    assert comparer.compared == [(b"ana",), (b"beto",)]


async def test_bulletin_watch_list_caches_and_reloads_after_the_window():
    calls = []

    async def load():
        calls.append(1)
        return PEOPLE

    watch_list = BulletinWatchList(load)
    assert await watch_list.people() == PEOPLE
    assert await watch_list.people() == PEOPLE
    assert len(calls) == 1
    watch_list._cached_at -= 60  # simula que pasó la ventana de caché
    await watch_list.people()
    assert len(calls) == 2
