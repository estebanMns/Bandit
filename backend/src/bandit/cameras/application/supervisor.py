"""Supervisor de captura: una tarea asyncio por cámara, con reconexión."""

import asyncio
import logging
from uuid import UUID

from bandit.cameras.application.frame_hub import FrameHub
from bandit.cameras.domain.models import Camera, CameraStatus, CameraStatusChanged, Frame
from bandit.cameras.domain.ports import (
    CameraRepository,
    FrameSource,
    FrameSourceUnavailableError,
    UnreadableUrlError,
    UrlCipher,
)
from bandit.shared.clock import Clock
from bandit.shared.events import EventBus

logger = logging.getLogger(__name__)

_MAX_BACKOFF_SECONDS = 30.0


class CaptureSupervisor:
    def __init__(
        self,
        cameras: CameraRepository,
        source: FrameSource,
        cipher: UrlCipher,
        hub: FrameHub,
        bus: EventBus,
        clock: Clock,
        initial_backoff: float = 1.0,
    ) -> None:
        self._cameras = cameras
        self._source = source
        self._cipher = cipher
        self._hub = hub
        self._bus = bus
        self._clock = clock
        self._initial_backoff = initial_backoff
        self._tasks: dict[UUID, asyncio.Task[None]] = {}
        self._running: dict[UUID, Camera] = {}
        self._statuses: dict[UUID, CameraStatus] = {}
        # Por qué una cámara no tiene video, para mostrarlo en la app. Nunca incluye la URL.
        self._problems: dict[UUID, str] = {}
        # URL cifrada de cada cámara que no se pudo leer: no se reintenta mientras no cambie.
        self._unreadable: dict[UUID, str] = {}

    def status_of(self, camera_id: UUID) -> CameraStatus:
        return self._statuses.get(camera_id, CameraStatus.STOPPED)

    def problem_of(self, camera_id: UUID) -> str | None:
        problem = self._problems.get(camera_id)
        return problem[:1].upper() + problem[1:] if problem else None

    async def start_all(self) -> None:
        for camera in await self._cameras.list_enabled():
            self.start(camera)

    async def reconcile(self) -> None:
        """Sigue a la base de datos, que comparten varios equipos (por ejemplo el PC y la Mac).

        Arranca las cámaras que otro equipo agregó o activó y detiene las que desactivó o borró.
        """
        enabled = {camera.id: camera for camera in await self._cameras.list_enabled()}
        for camera in enabled.values():
            if self._unreadable.get(camera.id) != camera.encrypted_url:
                self.start(camera)
        for camera_id in [known for known in self._running if known not in enabled]:
            await self.stop(self._running[camera_id])

    def start(self, camera: Camera) -> None:
        if camera.id in self._tasks:
            return
        self._running[camera.id] = camera
        self._tasks[camera.id] = asyncio.create_task(self._run(camera), name=f"captura-{camera.id}")

    async def stop(self, camera: Camera) -> None:
        self._running.pop(camera.id, None)
        task = self._tasks.pop(camera.id, None)
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await self._set_status(camera, CameraStatus.STOPPED)

    async def stop_all(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        self._running.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run(self, camera: Camera) -> None:
        try:
            url = self._cipher.decrypt(camera.encrypted_url)
        except UnreadableUrlError:
            # Reintentar no sirve: con esta clave la URL nunca se podrá leer.
            self._problems[camera.id] = (
                "Se guardó con otra CAMERA_ENCRYPTION_KEY: bórrala y conéctala de nuevo"
            )
            logger.warning(
                "No se puede leer la cámara %s: se guardó con otra CAMERA_ENCRYPTION_KEY. "
                "Vuelve a poner la clave anterior o bórrala y conéctala de nuevo.",
                camera.id,
            )
            self._unreadable[camera.id] = camera.encrypted_url
            self._tasks.pop(camera.id, None)
            self._running.pop(camera.id, None)
            await self._set_status(camera, CameraStatus.STOPPED)
            return
        self._unreadable.pop(camera.id, None)
        backoff = self._initial_backoff
        while True:
            await self._set_status(camera, CameraStatus.CONNECTING)
            try:
                async for jpeg in self._source.stream(url):
                    if self.status_of(camera.id) is not CameraStatus.LIVE:
                        self._problems.pop(camera.id, None)
                        await self._set_status(camera, CameraStatus.LIVE)
                        backoff = self._initial_backoff
                    self._hub.publish(Frame(camera.id, jpeg, self._clock.now()))
            except asyncio.CancelledError:
                raise
            except FrameSourceUnavailableError as error:
                if self._problems.get(camera.id) != str(error):
                    logger.warning("No se puede leer la cámara %s: %s", camera.id, error)
                self._problems[camera.id] = str(error)
            except Exception as error:
                # Solo el tipo: el mensaje podría incluir la URL con credenciales.
                logger.warning("Se perdió la cámara %s: %s", camera.id, type(error).__name__)

            await self._set_status(camera, CameraStatus.RETRYING)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)

    async def _set_status(self, camera: Camera, status: CameraStatus) -> None:
        self._statuses[camera.id] = status
        await self._bus.publish(
            CameraStatusChanged(
                camera_id=camera.id, establishment_id=camera.establishment_id, status=status
            )
        )
