"""Casos de uso de cámaras."""

from uuid import UUID, uuid4

from bandit.cameras.application.supervisor import CaptureSupervisor
from bandit.cameras.domain.models import Camera, validate_stream_url
from bandit.cameras.domain.ports import CameraRepository, UrlCipher
from bandit.shared.errors import NotFoundError


class RegisterCamera:
    def __init__(
        self, cameras: CameraRepository, cipher: UrlCipher, supervisor: CaptureSupervisor
    ) -> None:
        self._cameras = cameras
        self._cipher = cipher
        self._supervisor = supervisor

    async def execute(self, establishment_id: UUID, name: str, url: str) -> Camera:
        camera = Camera(
            id=uuid4(),
            establishment_id=establishment_id,
            name=name.strip(),
            encrypted_url=self._cipher.encrypt(validate_stream_url(url)),
        )
        await self._cameras.add(camera)
        self._supervisor.start(camera)
        return camera


class GetCamera:
    def __init__(self, cameras: CameraRepository) -> None:
        self._cameras = cameras

    async def execute(self, camera_id: UUID) -> Camera:
        camera = await self._cameras.get(camera_id)
        if camera is None:
            raise NotFoundError("La cámara no existe")
        return camera


class ListCameras:
    def __init__(self, cameras: CameraRepository) -> None:
        self._cameras = cameras

    async def execute(self, establishment_id: UUID) -> list[Camera]:
        return await self._cameras.list_for(establishment_id)


class SetCameraEnabled:
    def __init__(
        self, cameras: CameraRepository, get: GetCamera, supervisor: CaptureSupervisor
    ) -> None:
        self._cameras = cameras
        self._get = get
        self._supervisor = supervisor

    async def execute(self, camera_id: UUID, enabled: bool) -> Camera:
        camera = await self._get.execute(camera_id)
        camera.enabled = enabled
        await self._cameras.save(camera)
        if enabled:
            self._supervisor.start(camera)
        else:
            await self._supervisor.stop(camera)
        return camera


class RemoveCamera:
    def __init__(
        self, cameras: CameraRepository, get: GetCamera, supervisor: CaptureSupervisor
    ) -> None:
        self._cameras = cameras
        self._get = get
        self._supervisor = supervisor

    async def execute(self, camera_id: UUID) -> None:
        camera = await self._get.execute(camera_id)
        await self._supervisor.stop(camera)
        await self._cameras.delete(camera_id)
