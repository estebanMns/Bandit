"""Rutas de la prueba de rostros, para la página Actividad."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from bandit.faces.api.schemas import FaceCheckResponse, FaceWatchResponse
from bandit.faces.domain.models import FaceOutcome
from bandit.faces.module import FacesModule
from bandit.identity.public import CurrentUser
from bandit.shared.errors import NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api", tags=["faces"])


def _module(request: Request) -> FacesModule:
    module: FacesModule = request.app.state.faces
    return module


Module = Annotated[FacesModule, Depends(_module)]


@router.get("/establishments/{establishment_id}/face-checks")
async def get_face_checks(
    establishment_id: UUID, user: CurrentUser, module: Module
) -> FaceWatchResponse:
    if not user.can_access(establishment_id):
        raise PermissionDeniedError("No tienes acceso a este local")
    entry = module.log.for_establishment(establishment_id)
    people = await module.watch_list.people() if module.enabled else []
    return FaceWatchResponse(
        enabled=module.enabled,
        model=module.model,
        people=[person.name for person in people],
        used=module.limit.used,
        limit=module.limit.limit,
        counts={outcome: entry.counts[outcome] for outcome in FaceOutcome},
        recent=[FaceCheckResponse.of(check) for check in entry.recent],
    )


@router.get("/face-checks/{check_id}/frame")
async def get_face_check_frame(check_id: UUID, user: CurrentUser, module: Module) -> Response:
    found = module.log.frame(check_id)
    if found is None:
        raise NotFoundError("La imagen ya no está en memoria")
    establishment_id, jpeg = found
    if not user.can_access(establishment_id):
        raise PermissionDeniedError("No tienes acceso a este local")
    return Response(jpeg, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})
