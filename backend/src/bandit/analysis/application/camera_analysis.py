"""Decide qué fotogramas de una cámara van al modelo y cuándo hay una situación real."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from bandit.analysis.application.budget import DailyBudget
from bandit.analysis.domain.models import (
    SceneAssessment,
    SituationDetected,
    SituationType,
    mentions_identity,
)
from bandit.analysis.domain.ports import MotionDetector, SceneAnalyzer
from bandit.cameras.public import Camera, Frame
from bandit.shared.events import EventBus

logger = logging.getLogger(__name__)

_MIN_CONFIDENCE = 0.6
_CONFIRMING_INTERVAL_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class AnalysisPolicy:
    min_interval_seconds: float
    motion_threshold: float
    confirmation_frames: int
    cooldown_seconds: float


class CameraAnalysis:
    def __init__(
        self,
        camera: Camera,
        analyzer: SceneAnalyzer,
        motion: MotionDetector,
        budget: DailyBudget,
        limiter: asyncio.Semaphore,
        bus: EventBus,
        policy: AnalysisPolicy,
    ) -> None:
        self._camera = camera
        self._analyzer = analyzer
        self._motion = motion
        self._budget = budget
        self._limiter = limiter
        self._bus = bus
        self._policy = policy
        self._previous_jpeg: bytes | None = None
        self._last_sample: datetime | None = None
        self._last_alert: datetime | None = None
        self._streak_type = SituationType.NONE
        self._streak = 0

    @property
    def _confirming(self) -> bool:
        return self._streak > 0

    def _is_due(self, now: datetime) -> bool:
        if self._last_sample is None:
            return True
        interval = (
            _CONFIRMING_INTERVAL_SECONDS if self._confirming else self._policy.min_interval_seconds
        )
        return (now - self._last_sample).total_seconds() >= interval

    async def _has_motion(self, jpeg: bytes) -> bool:
        previous, self._previous_jpeg = self._previous_jpeg, jpeg
        if previous is None:
            return False
        score = await asyncio.to_thread(self._motion.score, previous, jpeg)
        return score >= self._policy.motion_threshold

    def _in_cooldown(self, now: datetime) -> bool:
        return (
            self._last_alert is not None
            and (now - self._last_alert).total_seconds() < self._policy.cooldown_seconds
        )

    async def _assess(self, jpeg: bytes) -> SceneAssessment | None:
        async with self._limiter:
            try:
                assessment = await self._analyzer.assess(jpeg)
            except Exception as error:
                logger.warning("Falló el análisis de %s: %s", self._camera.id, type(error).__name__)
                return None
        if mentions_identity(assessment.description):
            logger.warning("Se descartó una respuesta con identidad en %s", self._camera.id)
            return SceneAssessment.calm()
        return assessment

    async def on_frame(self, frame: Frame) -> None:
        now = frame.captured_at
        if not self._is_due(now):
            return
        self._last_sample = now
        moved = await self._has_motion(frame.jpeg)
        if not self._confirming and not moved:
            return
        if not self._budget.try_spend():
            return
        assessment = await self._assess(frame.jpeg)
        if assessment is not None:
            await self._update_streak(assessment, frame)

    async def _update_streak(self, assessment: SceneAssessment, frame: Frame) -> None:
        significant = (
            assessment.type is not SituationType.NONE and assessment.confidence >= _MIN_CONFIDENCE
        )
        if not significant:
            self._streak_type, self._streak = SituationType.NONE, 0
            return
        if assessment.type is self._streak_type:
            self._streak += 1
        else:
            self._streak_type, self._streak = assessment.type, 1
        if self._streak < self._policy.confirmation_frames:
            return

        self._streak_type, self._streak = SituationType.NONE, 0
        if self._in_cooldown(frame.captured_at):
            return
        self._last_alert = frame.captured_at
        await self._bus.publish(
            SituationDetected(
                camera_id=self._camera.id,
                establishment_id=self._camera.establishment_id,
                camera_name=self._camera.name,
                assessment=assessment,
                evidence_jpeg=frame.jpeg,
                detected_at=frame.captured_at,
            )
        )
