"""Mira cada cámara en vivo y compara a quien aparece con la lista de prueba."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from bandit.cameras.public import Camera, CameraStatus, CameraStatusChanged, FrameHub, GetCamera
from bandit.faces.domain.models import (
    DailyLimit,
    FaceCheck,
    FaceCheckDone,
    FaceOutcome,
    FaceVerdict,
    WatchedPerson,
)
from bandit.faces.domain.ports import FaceComparer, MotionDetector, WatchList
from bandit.shared.events import EventBus

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FacePolicy:
    min_interval_seconds: float
    motion_threshold: float


class AlertGate:
    """Una alerta por persona y local cada cierto tiempo, aunque la vean varias cámaras."""

    def __init__(self, cooldown_seconds: float) -> None:
        self._cooldown = timedelta(seconds=cooldown_seconds)
        self._last: dict[tuple[UUID, str], datetime] = {}

    def allow(self, establishment_id: UUID, person: str, at: datetime) -> bool:
        key = (establishment_id, person)
        last = self._last.get(key)
        if last is not None and at - last < self._cooldown:
            return False
        self._last[key] = at
        return True


class CameraFaceWatch:
    """Una cámara: filtra por tiempo y movimiento, compara y avisa una vez por persona."""

    def __init__(
        self,
        camera: Camera,
        comparer: FaceComparer,
        watch_list: WatchList,
        motion: MotionDetector,
        limit: DailyLimit,
        bus: EventBus,
        policy: FacePolicy,
        alerts: AlertGate,
    ) -> None:
        self._camera = camera
        self._comparer = comparer
        self._watch_list = watch_list
        self._motion = motion
        self._limit = limit
        self._bus = bus
        self._policy = policy
        self._alerts = alerts
        self._previous: bytes | None = None
        self._last_check: datetime | None = None

    async def on_frame(self, jpeg: bytes, at: datetime) -> None:
        if self._last_check and at - self._last_check < timedelta(
            seconds=self._policy.min_interval_seconds
        ):
            return
        previous, self._previous = self._previous, jpeg
        if previous is not None and self._motion.score(previous, jpeg) < (
            self._policy.motion_threshold
        ):
            return
        people = await self._watch_list.people()
        if not people or not self._limit.try_spend():
            return
        self._last_check = at
        outcome, person, verdict = await self._compare(people, jpeg)
        alerted = (
            outcome is FaceOutcome.MATCH
            and person is not None
            and self._alerts.allow(self._camera.establishment_id, person, at)
        )
        check = FaceCheck(
            id=uuid4(),
            camera_id=self._camera.id,
            camera_name=self._camera.name,
            establishment_id=self._camera.establishment_id,
            at=at,
            outcome=outcome,
            person=person,
            confidence=verdict.confidence,
            explanation=verdict.explanation,
            alerted=alerted,
        )
        await self._bus.publish(FaceCheckDone(check=check, jpeg=jpeg))

    async def _compare(
        self, people: list[WatchedPerson], jpeg: bytes
    ) -> tuple[FaceOutcome, str | None, FaceVerdict]:
        # Si nadie coincide se muestra la respuesta sobre la primera persona de la lista.
        first: FaceVerdict | None = None
        for watched in people:
            try:
                verdict = await self._comparer.compare(watched.references, jpeg)
            except Exception as error:
                logger.warning("Falló la comparación de rostros: %s", type(error).__name__)
                return FaceOutcome.ERROR, None, FaceVerdict(False, False, 0.0, type(error).__name__)
            if not verdict.face_visible:
                return FaceOutcome.NO_FACE, None, verdict
            if verdict.confident_match:
                return FaceOutcome.MATCH, watched.name, verdict
            first = first or verdict
        assert first is not None
        return FaceOutcome.NO_MATCH, None, first


class FaceSupervisor:
    """Una tarea por cámara en vivo, igual que el análisis de situaciones."""

    def __init__(
        self,
        frames: FrameHub,
        get_camera: GetCamera,
        comparer: FaceComparer,
        watch_list: WatchList,
        motion: MotionDetector,
        limit: DailyLimit,
        bus: EventBus,
        policy: FacePolicy,
        alerts: AlertGate,
    ) -> None:
        self._frames = frames
        self._get_camera = get_camera
        self._comparer = comparer
        self._watch_list = watch_list
        self._motion = motion
        self._limit = limit
        self._bus = bus
        self._policy = policy
        self._alerts = alerts
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    async def on_camera_status(self, event: CameraStatusChanged) -> None:
        if event.status is CameraStatus.LIVE and event.camera_id not in self._tasks:
            camera = await self._get_camera.execute(event.camera_id)
            self._tasks[camera.id] = asyncio.create_task(self._run(camera))
        elif event.status is CameraStatus.STOPPED:
            task = self._tasks.pop(event.camera_id, None)
            if task is not None:
                task.cancel()

    async def stop_all(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks.clear()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _run(self, camera: Camera) -> None:
        watch = CameraFaceWatch(
            camera,
            self._comparer,
            self._watch_list,
            self._motion,
            self._limit,
            self._bus,
            self._policy,
            self._alerts,
        )
        subscription = self._frames.subscribe(camera.id)
        try:
            async for frame in subscription:
                try:
                    await watch.on_frame(frame.jpeg, frame.captured_at)
                except Exception:
                    logger.exception("La prueba de rostros falló en un fotograma")
        finally:
            self._frames.unsubscribe(camera.id, subscription)
