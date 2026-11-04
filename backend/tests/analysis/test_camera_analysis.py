import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from bandit.analysis.application.budget import DailyBudget
from bandit.analysis.application.camera_analysis import AnalysisPolicy, CameraAnalysis
from bandit.analysis.domain.models import (
    SceneAssessment,
    Severity,
    SituationDetected,
    SituationType,
)
from bandit.cameras.public import Camera, Frame
from bandit.shared.events import InMemoryEventBus

START = datetime(2026, 11, 4, 22, 0, tzinfo=UTC)
FIGHT = SceneAssessment(SituationType.FIGHT, Severity.HIGH, 0.9, "Pelea en la barra.")
WEAK_FIGHT = SceneAssessment(SituationType.FIGHT, Severity.LOW, 0.3, "Tal vez una pelea.")
CALM = SceneAssessment.calm()


class FakeAnalyzer:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0

    async def assess(self, jpeg):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeMotion:
    def __init__(self, score=1.0):
        self.value = score

    def score(self, previous, current):
        return self.value


@pytest.fixture
def alerts():
    return []


def build(analyzer, alerts, clock, motion=None, limit=100, frames=2, cooldown=120):
    bus = InMemoryEventBus()

    async def record(event: SituationDetected) -> None:
        alerts.append(event)

    bus.subscribe(SituationDetected, record)
    camera = Camera(uuid4(), uuid4(), "Barra", "cifrada")
    analysis = CameraAnalysis(
        camera,
        analyzer,
        motion or FakeMotion(),
        DailyBudget(limit, clock),
        asyncio.Semaphore(1),
        bus,
        AnalysisPolicy(
            min_interval_seconds=10,
            motion_threshold=0.02,
            confirmation_frames=frames,
            cooldown_seconds=cooldown,
        ),
    )
    return analysis, camera


def frame(camera, seconds):
    return Frame(camera.id, b"jpeg", START + timedelta(seconds=seconds))


async def feed(analysis, camera, *seconds):
    for moment in seconds:
        await analysis.on_frame(frame(camera, moment))


async def test_first_frame_only_sets_the_motion_reference(clock, alerts):
    analyzer = FakeAnalyzer()
    analysis, camera = build(analyzer, alerts, clock)

    await feed(analysis, camera, 0)

    assert analyzer.calls == 0


async def test_situation_must_repeat_before_alerting(clock, alerts):
    analyzer = FakeAnalyzer(FIGHT, FIGHT)
    analysis, camera = build(analyzer, alerts, clock)

    await feed(analysis, camera, 0, 10)
    assert alerts == []

    await feed(analysis, camera, 12)

    assert len(alerts) == 1
    assert alerts[0].assessment.type is SituationType.FIGHT
    assert alerts[0].evidence_jpeg == b"jpeg"


async def test_a_single_false_positive_never_alerts(clock, alerts):
    analyzer = FakeAnalyzer(FIGHT, CALM)
    analysis, camera = build(analyzer, alerts, clock)

    await feed(analysis, camera, 0, 10, 12)

    assert alerts == []


async def test_low_confidence_is_ignored(clock, alerts):
    analyzer = FakeAnalyzer(WEAK_FIGHT, WEAK_FIGHT)
    analysis, camera = build(analyzer, alerts, clock)

    await feed(analysis, camera, 0, 10, 20)

    assert alerts == []


async def test_quiet_scene_does_not_call_the_model(clock, alerts):
    analyzer = FakeAnalyzer()
    analysis, camera = build(analyzer, alerts, clock, motion=FakeMotion(score=0.0))

    await feed(analysis, camera, 0, 10, 20, 30)

    assert analyzer.calls == 0


async def test_frames_inside_the_interval_are_skipped(clock, alerts):
    analyzer = FakeAnalyzer(CALM)
    analysis, camera = build(analyzer, alerts, clock)

    await feed(analysis, camera, 0, 1, 2, 3, 10)

    assert analyzer.calls == 1


async def test_daily_budget_stops_calls(clock, alerts):
    analyzer = FakeAnalyzer(CALM, CALM)
    analysis, camera = build(analyzer, alerts, clock, limit=2)

    await feed(analysis, camera, 0, 10, 20, 30, 40)

    assert analyzer.calls == 2


async def test_cooldown_prevents_duplicate_alerts(clock, alerts):
    analyzer = FakeAnalyzer(*[FIGHT] * 4)
    analysis, camera = build(analyzer, alerts, clock)

    await feed(analysis, camera, 0, 10, 12, 22, 24)

    assert len(alerts) == 1


async def test_identity_response_is_discarded(clock, alerts):
    named = SceneAssessment(SituationType.ROBBERY, Severity.HIGH, 0.9, "Pedro se llama el ladrón.")
    analyzer = FakeAnalyzer(named, named)
    analysis, camera = build(analyzer, alerts, clock)

    await feed(analysis, camera, 0, 10, 20)

    assert alerts == []


async def test_model_failure_does_not_stop_the_analysis(clock, alerts):
    analyzer = FakeAnalyzer(RuntimeError("caído"), FIGHT, FIGHT)
    analysis, camera = build(analyzer, alerts, clock)

    await feed(analysis, camera, 0, 10, 20, 22)

    assert len(alerts) == 1
