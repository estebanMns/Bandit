"""La prueba de rostros solo alerta con una coincidencia segura, una vez por persona."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from bandit.cameras.public import Camera
from bandit.faces.application.log import FaceLog
from bandit.faces.application.watcher import AlertGate, CameraFaceWatch, FacePolicy
from bandit.faces.domain.models import (
    DailyLimit,
    FaceCheckDone,
    FaceOutcome,
    FaceVerdict,
    WatchedPerson,
)
from bandit.faces.infrastructure.reference_folder import ReferenceFolderWatchList
from bandit.shared.events import InMemoryEventBus

START = datetime(2026, 11, 12, 20, 0, tzinfo=UTC)
MATCH = FaceVerdict(True, True, 0.95, "Mismos rasgos.")
OTHER = FaceVerdict(True, False, 0.9, "Otra persona.")
DOUBT = FaceVerdict(True, True, 0.6, "Se parece, pero no es seguro.")
EMPTY = FaceVerdict(False, False, 0.9, "No hay nadie.")


class Clock:
    def now(self):
        return START


class Comparer:
    def __init__(self, *verdicts):
        self.verdicts = list(verdicts)
        self.calls = 0

    async def compare(self, references, probe):
        self.calls += 1
        verdict = self.verdicts.pop(0)
        if isinstance(verdict, Exception):
            raise verdict
        return verdict


class People:
    def __init__(self, people):
        self.list = people

    async def people(self):
        return self.list


class Motion:
    def __init__(self, value=1.0):
        self.value = value

    def score(self, previous, current):
        return self.value


def build(comparer, people=None, motion=None, limit=100, cooldown=600, gate=None, place=None):
    bus = InMemoryEventBus()
    events = []

    async def collect(event: FaceCheckDone):
        events.append(event)

    bus.subscribe(FaceCheckDone, collect)
    watch = CameraFaceWatch(
        Camera(uuid4(), place or uuid4(), "Entrada", ""),
        comparer,
        People([WatchedPerson("Persona Prueba", (b"ref",))] if people is None else people),
        motion or Motion(),
        DailyLimit(limit, Clock()),
        bus,
        FacePolicy(min_interval_seconds=5, motion_threshold=0.02),
        gate or AlertGate(cooldown),
    )
    return watch, events


def at(seconds):
    return START + timedelta(seconds=seconds)


async def test_each_outcome_is_reported_and_only_a_confident_match_alerts():
    watch, events = build(Comparer(OTHER, DOUBT, EMPTY, MATCH))

    for second in (0, 10, 20, 30):
        await watch.on_frame(b"x", at(second))

    checks = [event.check for event in events]
    assert [c.outcome for c in checks] == [
        FaceOutcome.NO_MATCH,
        FaceOutcome.NO_MATCH,
        FaceOutcome.NO_FACE,
        FaceOutcome.MATCH,
    ]
    assert [c.alerted for c in checks] == [False, False, False, True]
    assert checks[3].person == "Persona Prueba"
    assert checks[0].person is None


async def test_the_same_person_alerts_again_only_after_the_cooldown():
    watch, events = build(Comparer(MATCH, MATCH, MATCH), cooldown=60)

    for second in (0, 10, 70):
        await watch.on_frame(b"x", at(second))

    assert [event.check.alerted for event in events] == [True, False, True]


async def test_frames_too_close_or_without_motion_are_not_compared():
    comparer = Comparer(OTHER)
    watch, events = build(comparer, motion=Motion(0.0))

    await watch.on_frame(b"a", at(0))
    await watch.on_frame(b"b", at(1))
    await watch.on_frame(b"c", at(10))

    assert comparer.calls == 1
    assert len(events) == 1


async def test_nothing_is_compared_without_consented_people_or_budget():
    comparer = Comparer()
    watch, events = build(comparer, people=[])
    await watch.on_frame(b"x", at(0))

    limited, limited_events = build(comparer, limit=0)
    await limited.on_frame(b"x", at(0))

    assert comparer.calls == 0
    assert events == limited_events == []


async def test_a_failed_comparison_is_an_error_not_a_match():
    watch, events = build(Comparer(RuntimeError("caído")))

    await watch.on_frame(b"x", at(0))

    assert events[0].check.outcome is FaceOutcome.ERROR
    assert events[0].check.alerted is False


async def test_the_log_counts_outcomes_and_keeps_the_frame_in_memory():
    watch, events = build(Comparer(OTHER, MATCH))
    await watch.on_frame(b"uno", at(0))
    await watch.on_frame(b"dos", at(10))
    log = FaceLog()

    for event in events:
        await log.record(event)

    entry = log.for_establishment(events[0].check.establishment_id)
    assert entry.counts[FaceOutcome.MATCH] == 1
    assert entry.counts[FaceOutcome.NO_MATCH] == 1
    assert entry.recent[0].outcome is FaceOutcome.MATCH
    assert log.frame(events[1].check.id)[1] == b"dos"


async def test_references_come_only_from_each_consented_persons_folder(tmp_path):
    (tmp_path / "persona-prueba").mkdir()
    for index in range(5):
        (tmp_path / "persona-prueba" / f"r{index}.jpg").write_bytes(b"foto")

    async def source():
        return [("Persona Prueba", "persona-prueba"), ("Sin Fotos", "sin-fotos")]

    people = await ReferenceFolderWatchList(str(tmp_path), source).people()

    assert [p.name for p in people] == ["Persona Prueba"]
    assert len(people[0].references) == 3


async def test_two_cameras_of_the_same_place_create_a_single_alert():
    gate, place = AlertGate(600), uuid4()
    entrance, entrance_events = build(Comparer(MATCH), gate=gate, place=place)
    bar, bar_events = build(Comparer(MATCH), gate=gate, place=place)

    await entrance.on_frame(b"x", at(0))
    await bar.on_frame(b"x", at(1))

    assert entrance_events[0].check.alerted is True
    assert bar_events[0].check.alerted is False
