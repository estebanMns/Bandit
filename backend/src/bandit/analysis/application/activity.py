"""Memoria corta de lo que el modelo ha visto, para el panel. Nada se guarda en disco."""

from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from bandit.analysis.domain.models import ActivityOutcome, AnalysisActivity, SceneAssessment

RECENT_LIMIT = 50


@dataclass(frozen=True, slots=True)
class ActivityEntry:
    at: datetime
    outcome: ActivityOutcome
    motion: float
    assessment: SceneAssessment | None
    streak: int
    streak_target: int
    alerted: bool


@dataclass(slots=True)
class CameraActivity:
    camera_id: UUID
    camera_name: str
    establishment_id: UUID
    day: date
    recent: deque[ActivityEntry] = field(default_factory=lambda: deque(maxlen=RECENT_LIMIT))
    counts: Counter[ActivityOutcome] = field(default_factory=Counter)
    last_frame: bytes | None = None
    last_frame_at: datetime | None = None


class ActivityTracker:
    def __init__(self) -> None:
        self._cameras: dict[UUID, CameraActivity] = {}

    async def record(self, event: AnalysisActivity) -> None:
        activity = self._cameras.get(event.camera_id)
        if activity is None or activity.day != event.at.date():
            activity = self._fresh(event, activity)
            self._cameras[event.camera_id] = activity
        activity.camera_name = event.camera_name
        activity.counts[event.outcome] += 1
        activity.recent.appendleft(
            ActivityEntry(
                at=event.at,
                outcome=event.outcome,
                motion=event.motion,
                assessment=event.assessment,
                streak=event.streak,
                streak_target=event.streak_target,
                alerted=event.alerted,
            )
        )
        if event.jpeg is not None:
            activity.last_frame, activity.last_frame_at = event.jpeg, event.at

    @staticmethod
    def _fresh(event: AnalysisActivity, previous: CameraActivity | None) -> CameraActivity:
        """Al cambiar de día se reinician los contadores, pero se conserva lo reciente."""
        activity = CameraActivity(
            camera_id=event.camera_id,
            camera_name=event.camera_name,
            establishment_id=event.establishment_id,
            day=event.at.date(),
        )
        if previous is not None:
            activity.recent.extend(previous.recent)
            activity.last_frame, activity.last_frame_at = (
                previous.last_frame,
                previous.last_frame_at,
            )
        return activity

    def for_establishment(self, establishment_id: UUID) -> list[CameraActivity]:
        cameras = [a for a in self._cameras.values() if a.establishment_id == establishment_id]
        return sorted(cameras, key=lambda activity: activity.camera_name)

    def get(self, camera_id: UUID) -> CameraActivity | None:
        return self._cameras.get(camera_id)
