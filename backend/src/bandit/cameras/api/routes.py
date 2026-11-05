"""Rutas de cámaras y video en vivo."""

import contextlib
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from bandit.cameras.domain.models import Camera, CameraStatus, Frame
from bandit.cameras.module import CamerasModule
from bandit.identity.public import (
    CurrentUser,
    ManagerUser,
    User,
    authenticate_websocket,
    require_csrf,
)
from bandit.shared.errors import DomainError, PermissionDeniedError
from bandit.shared.ws import pump

router = APIRouter(prefix="/api", tags=["cameras"])
video_router = APIRouter()


def _module(request: Request) -> CamerasModule:
    module: CamerasModule = request.app.state.cameras
    return module


Module = Annotated[CamerasModule, Depends(_module)]


class CreateCameraRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=8, max_length=2000)


class UpdateCameraRequest(BaseModel):
    enabled: bool


class CameraResponse(BaseModel):
    """Nunca incluye la URL: puede contener credenciales."""

    id: UUID
    establishment_id: UUID
    name: str
    enabled: bool
    status: CameraStatus


def _response(camera: Camera, module: CamerasModule) -> CameraResponse:
    return CameraResponse(
        id=camera.id,
        establishment_id=camera.establishment_id,
        name=camera.name,
        enabled=camera.enabled,
        status=module.supervisor.status_of(camera.id),
    )


def _ensure_access(user: User, establishment_id: UUID) -> None:
    if not user.can_access(establishment_id):
        raise PermissionDeniedError("No tienes acceso a este local")


@router.get("/establishments/{establishment_id}/cameras")
async def list_cameras(
    establishment_id: UUID, user: CurrentUser, module: Module
) -> list[CameraResponse]:
    _ensure_access(user, establishment_id)
    return [_response(c, module) for c in await module.list_for.execute(establishment_id)]


@router.post(
    "/establishments/{establishment_id}/cameras",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_csrf)],
)
async def create_camera(
    establishment_id: UUID, body: CreateCameraRequest, user: ManagerUser, module: Module
) -> CameraResponse:
    _ensure_access(user, establishment_id)
    return _response(await module.register.execute(establishment_id, body.name, body.url), module)


@router.patch("/cameras/{camera_id}", dependencies=[Depends(require_csrf)])
async def update_camera(
    camera_id: UUID, body: UpdateCameraRequest, user: ManagerUser, module: Module
) -> CameraResponse:
    _ensure_access(user, (await module.get.execute(camera_id)).establishment_id)
    return _response(await module.set_enabled.execute(camera_id, body.enabled), module)


@router.delete(
    "/cameras/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def delete_camera(camera_id: UUID, user: ManagerUser, module: Module) -> None:
    _ensure_access(user, (await module.get.execute(camera_id)).establishment_id)
    await module.remove.execute(camera_id)


@video_router.websocket("/ws/video/{camera_id}")
async def video(websocket: WebSocket, camera_id: UUID) -> None:
    module: CamerasModule = websocket.app.state.cameras
    try:
        user = await authenticate_websocket(websocket)
        camera = await module.get.execute(camera_id)
        _ensure_access(user, camera.establishment_id)
    except DomainError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    subscription = module.frames.subscribe(camera_id)

    async def send(frame: Frame) -> None:
        await websocket.send_bytes(frame.jpeg)

    try:
        await pump(websocket, subscription, send)
    finally:
        module.frames.unsubscribe(camera_id, subscription)
        with contextlib.suppress(WebSocketDisconnect, RuntimeError):
            await websocket.close()
