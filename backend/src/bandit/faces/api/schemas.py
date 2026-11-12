from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from bandit.faces.domain.models import FaceCheck, FaceOutcome


class FaceCheckResponse(BaseModel):
    id: UUID
    camera_id: UUID
    camera_name: str
    at: datetime
    outcome: FaceOutcome
    person: str | None
    confidence: float
    explanation: str
    alerted: bool

    @classmethod
    def of(cls, check: FaceCheck) -> "FaceCheckResponse":
        return cls(
            id=check.id,
            camera_id=check.camera_id,
            camera_name=check.camera_name,
            at=check.at,
            outcome=check.outcome,
            person=check.person,
            confidence=round(check.confidence, 3),
            explanation=check.explanation,
            alerted=check.alerted,
        )


class FaceWatchResponse(BaseModel):
    enabled: bool
    model: str | None
    people: list[str]
    used: int
    limit: int
    counts: dict[FaceOutcome, int]
    recent: list[FaceCheckResponse]
