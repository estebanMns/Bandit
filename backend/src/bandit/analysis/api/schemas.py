"""Formas de la API de actividad del modelo. Compartidas con el canal en vivo."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from bandit.analysis.application.activity import ActivityEntry, CameraActivity
from bandit.analysis.domain.models import ActivityOutcome, AnalysisActivity, SceneAssessment


class AssessmentResponse(BaseModel):
    type: str
    severity: str
    confidence: float
    description: str

    @classmethod
    def of(cls, assessment: SceneAssessment | None) -> "AssessmentResponse | None":
        if assessment is None:
            return None
        return cls(
            type=assessment.type.value,
            severity=assessment.severity.value,
            confidence=assessment.confidence,
            description=assessment.description,
        )


class ActivityEntryResponse(BaseModel):
    camera_id: UUID
    at: datetime
    outcome: ActivityOutcome
    motion: float
    assessment: AssessmentResponse | None
    streak: int
    streak_target: int
    alerted: bool

    @classmethod
    def of(
        cls, camera_id: UUID, entry: ActivityEntry | AnalysisActivity
    ) -> "ActivityEntryResponse":
        return cls(
            camera_id=camera_id,
            at=entry.at,
            outcome=entry.outcome,
            motion=round(entry.motion, 4),
            assessment=AssessmentResponse.of(entry.assessment),
            streak=entry.streak,
            streak_target=entry.streak_target,
            alerted=entry.alerted,
        )


class CameraActivityResponse(BaseModel):
    camera_id: UUID
    camera_name: str
    counts: dict[ActivityOutcome, int]
    has_frame: bool
    last_frame_at: datetime | None
    recent: list[ActivityEntryResponse]

    @classmethod
    def of(cls, activity: CameraActivity) -> "CameraActivityResponse":
        return cls(
            camera_id=activity.camera_id,
            camera_name=activity.camera_name,
            counts={outcome: activity.counts.get(outcome, 0) for outcome in ActivityOutcome},
            has_frame=activity.last_frame is not None,
            last_frame_at=activity.last_frame_at,
            recent=[ActivityEntryResponse.of(activity.camera_id, e) for e in activity.recent],
        )


class BudgetResponse(BaseModel):
    used: int
    limit: int


class ActivityResponse(BaseModel):
    model_enabled: bool
    budget: BudgetResponse
    cameras: list[CameraActivityResponse]
