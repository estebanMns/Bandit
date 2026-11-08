"""Rutas del panel de actividad del modelo."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from bandit.analysis.api.schemas import ActivityResponse, BudgetResponse, CameraActivityResponse
from bandit.analysis.module import AnalysisModule
from bandit.identity.public import CurrentUser, User
from bandit.shared.errors import NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api", tags=["analysis"])


def _module(request: Request) -> AnalysisModule:
    module: AnalysisModule = request.app.state.analysis
    return module


Module = Annotated[AnalysisModule, Depends(_module)]


def _ensure_access(user: User, establishment_id: UUID) -> None:
    if not user.can_access(establishment_id):
        raise PermissionDeniedError("No tienes acceso a este local")


@router.get("/establishments/{establishment_id}/analysis-activity")
async def get_activity(
    establishment_id: UUID, user: CurrentUser, module: Module
) -> ActivityResponse:
    _ensure_access(user, establishment_id)
    return ActivityResponse(
        model_enabled=module.model_enabled,
        budget=BudgetResponse(used=module.budget.used, limit=module.budget.limit),
        cameras=[
            CameraActivityResponse.of(activity)
            for activity in module.activity.for_establishment(establishment_id)
        ],
    )


@router.get("/analysis/cameras/{camera_id}/last-frame")
async def get_last_frame(camera_id: UUID, user: CurrentUser, module: Module) -> Response:
    activity = module.activity.get(camera_id)
    if activity is None or activity.last_frame is None:
        raise NotFoundError("Todavía no hay un fotograma analizado")
    _ensure_access(user, activity.establishment_id)
    return Response(
        activity.last_frame, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"}
    )
