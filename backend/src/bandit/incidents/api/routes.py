"""Rutas de incidentes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from bandit.identity.public import CurrentUser, User, require_csrf
from bandit.incidents.api.schemas import IncidentResponse
from bandit.incidents.domain.models import Incident
from bandit.incidents.module import IncidentsModule
from bandit.shared.errors import NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api", tags=["incidents"])


def _module(request: Request) -> IncidentsModule:
    module: IncidentsModule = request.app.state.incidents
    return module


Module = Annotated[IncidentsModule, Depends(_module)]


def _ensure_access(user: User, establishment_id: UUID) -> None:
    if not user.can_access(establishment_id):
        raise PermissionDeniedError("No tienes acceso a este local")


async def _authorized(incident_id: UUID, user: User, module: IncidentsModule) -> Incident:
    incident = await module.get.execute(incident_id)
    _ensure_access(user, incident.establishment_id)
    return incident


@router.get("/establishments/{establishment_id}/incidents")
async def list_incidents(
    establishment_id: UUID,
    user: CurrentUser,
    module: Module,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[IncidentResponse]:
    _ensure_access(user, establishment_id)
    incidents = await module.list_recent.execute(establishment_id, limit)
    return [IncidentResponse.of(incident) for incident in incidents]


@router.get("/incidents/{incident_id}")
async def get_incident(incident_id: UUID, user: CurrentUser, module: Module) -> IncidentResponse:
    return IncidentResponse.of(await _authorized(incident_id, user, module))


@router.get("/incidents/{incident_id}/evidence")
async def get_evidence(incident_id: UUID, user: CurrentUser, module: Module) -> Response:
    await _authorized(incident_id, user, module)
    jpeg = await module.evidence.load(incident_id)
    if jpeg is None:
        raise NotFoundError("La evidencia ya no está disponible")
    return Response(jpeg, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})


@router.post("/incidents/{incident_id}/confirm", dependencies=[Depends(require_csrf)])
async def confirm_incident(
    incident_id: UUID, user: CurrentUser, module: Module
) -> IncidentResponse:
    await _authorized(incident_id, user, module)
    return IncidentResponse.of(await module.confirm.execute(incident_id, user.email))


@router.post("/incidents/{incident_id}/discard", dependencies=[Depends(require_csrf)])
async def discard_incident(
    incident_id: UUID, user: CurrentUser, module: Module
) -> IncidentResponse:
    await _authorized(incident_id, user, module)
    return IncidentResponse.of(await module.discard.execute(incident_id, user.email))
