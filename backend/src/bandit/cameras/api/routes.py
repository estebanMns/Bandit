"""Rutas de cámaras y video en vivo."""

import contextlib
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from bandit.cameras.domain.discovery import ConnectOutcome, DiscoveredDevice
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


class ScanRequest(BaseModel):
    network: str = Field(min_length=7, max_length=40)


class DeviceResponse(BaseModel):
    ip: str
    open_ports: list[int]
    brand: str | None
    rtsp_server: str | None
    http_server: str | None
    looks_like_camera: bool

    @classmethod
    def of(cls, device: DiscoveredDevice) -> "DeviceResponse":
        return cls(
            ip=device.ip,
            open_ports=list(device.open_ports),
            brand=device.brand,
            rtsp_server=device.rtsp_server,
            http_server=device.http_server,
            looks_like_camera=device.has_rtsp,
        )


class ConnectRequest(BaseModel):
    ip: str = Field(min_length=7, max_length=15)
    username: str = Field(default="admin", max_length=100)
    password: str = Field(max_length=200)


class StreamResponse(BaseModel):
    path: str
    label: str
    source: str


class ConnectResponse(BaseModel):
    """Nunca devuelve la clave: el navegador arma la URL con la que escribió el usuario."""

    outcome: ConnectOutcome
    port: int
    tried: int
    ai_used: bool
    streams: list[StreamResponse]


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


@router.post("/establishments/{establishment_id}/camera-scan", dependencies=[Depends(require_csrf)])
async def scan_network(
    establishment_id: UUID, body: ScanRequest, user: ManagerUser, module: Module
) -> list[DeviceResponse]:
    _ensure_access(user, establishment_id)
    devices = await module.scan_network.execute(establishment_id, body.network)
    return [DeviceResponse.of(device) for device in devices]


@router.post(
    "/establishments/{establishment_id}/camera-scan/connect",
    dependencies=[Depends(require_csrf)],
)
async def connect_device(
    establishment_id: UUID, body: ConnectRequest, user: ManagerUser, module: Module
) -> ConnectResponse:
    _ensure_access(user, establishment_id)
    result = await module.connect_device.execute(body.ip, body.username, body.password)
    return ConnectResponse(
        outcome=result.outcome,
        port=result.port,
        tried=result.tried,
        ai_used=result.ai_used,
        streams=[
            StreamResponse(path=stream.path, label=stream.label, source=stream.source)
            for stream in result.streams
        ],
    )
