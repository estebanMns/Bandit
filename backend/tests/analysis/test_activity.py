"""El panel de actividad ve cada muestreo, sin guardar nada en disco ni nombrar personas."""

from datetime import timedelta
from uuid import uuid4

from bandit.analysis.application.activity import RECENT_LIMIT, ActivityTracker
from bandit.analysis.domain.models import (
    ActivityOutcome,
    AnalysisActivity,
    SceneAssessment,
    Severity,
    SituationType,
)
from tests.analysis.test_camera_analysis import (
    CALM,
    FIGHT,
    START,
    FakeAnalyzer,
    FakeMotion,
    build,
    feed,
)


def collect(analysis):
    """Engancha un registro de actividad al bus de la cámara bajo prueba."""
    tracker = ActivityTracker()
    analysis._bus.subscribe(AnalysisActivity, tracker.record)
    return tracker


def outcomes(tracker, camera):
    return [entry.outcome for entry in reversed(tracker.get(camera.id).recent)]


async def test_every_sample_is_reported_with_its_outcome(clock):
    alerts: list[object] = []
    analyzer = FakeAnalyzer(CALM, RuntimeError("caído"))
    analysis, camera = build(analyzer, alerts, clock, limit=2)
    tracker = collect(analysis)

    await feed(analysis, camera, 0, 10, 20, 30)

    assert outcomes(tracker, camera) == [
        ActivityOutcome.NO_MOTION,
        ActivityOutcome.ANALYZED,
        ActivityOutcome.ERROR,
        ActivityOutcome.OVER_BUDGET,
    ]


async def test_quiet_scene_is_reported_without_a_frame(clock):
    alerts: list[object] = []
    analysis, camera = build(FakeAnalyzer(), alerts, clock, motion=FakeMotion(score=0.0))
    tracker = collect(analysis)

    await feed(analysis, camera, 0, 10)

    activity = tracker.get(camera.id)
    assert activity.counts[ActivityOutcome.NO_MOTION] == 2
    assert activity.last_frame is None


async def test_analyzed_frame_is_kept_in_memory(clock):
    alerts: list[object] = []
    analysis, camera = build(FakeAnalyzer(CALM), alerts, clock)
    tracker = collect(analysis)

    await feed(analysis, camera, 0, 10)

    activity = tracker.get(camera.id)
    assert activity.last_frame == b"jpeg"
    assert activity.recent[0].assessment == CALM


async def test_streak_and_alert_are_visible(clock):
    alerts: list[object] = []
    analysis, camera = build(FakeAnalyzer(FIGHT, FIGHT), alerts, clock)
    tracker = collect(analysis)

    await feed(analysis, camera, 0, 10, 12)

    first, second = list(reversed(tracker.get(camera.id).recent))[1:]
    assert (first.streak, first.streak_target, first.alerted) == (1, 2, False)
    assert second.alerted is True
    assert len(alerts) == 1


async def test_identity_answers_are_reported_as_filtered(clock):
    alerts: list[object] = []
    named = SceneAssessment(SituationType.ROBBERY, Severity.HIGH, 0.9, "Pedro se llama el ladrón.")
    analysis, camera = build(FakeAnalyzer(named), alerts, clock)
    tracker = collect(analysis)

    await feed(analysis, camera, 0, 10)

    entry = tracker.get(camera.id).recent[0]
    assert entry.outcome is ActivityOutcome.FILTERED
    assert "Pedro" not in entry.assessment.description


def event(camera_id, establishment_id, at, outcome=ActivityOutcome.NO_MOTION):
    return AnalysisActivity(
        camera_id=camera_id,
        establishment_id=establishment_id,
        camera_name="Barra",
        at=at,
        outcome=outcome,
        motion=0.0,
        assessment=None,
        streak=0,
        streak_target=2,
        alerted=False,
        jpeg=None,
    )


async def test_recent_history_is_bounded():
    tracker = ActivityTracker()
    camera, local = uuid4(), uuid4()

    for second in range(RECENT_LIMIT + 10):
        await tracker.record(event(camera, local, START + timedelta(seconds=second)))

    assert len(tracker.get(camera).recent) == RECENT_LIMIT


async def test_counters_restart_each_day_but_history_stays():
    tracker = ActivityTracker()
    camera, local = uuid4(), uuid4()
    await tracker.record(event(camera, local, START))
    await tracker.record(event(camera, local, START + timedelta(days=1)))

    activity = tracker.get(camera)
    assert activity.counts[ActivityOutcome.NO_MOTION] == 1
    assert len(activity.recent) == 2


async def test_each_local_only_sees_its_cameras():
    tracker = ActivityTracker()
    mine, other = uuid4(), uuid4()
    await tracker.record(event(uuid4(), mine, START))
    await tracker.record(event(uuid4(), other, START))

    assert len(tracker.for_establishment(mine)) == 1
