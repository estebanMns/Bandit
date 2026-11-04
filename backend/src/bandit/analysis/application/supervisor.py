"""Mantiene una tarea de análisis por cada cámara en vivo."""

import asyncio
import logging
from uuid import UUID

from bandit.analysis.application.budget import DailyBudget
from bandit.analysis.application.camera_analysis import AnalysisPolicy, CameraAnalysis
from bandit.analysis.domain.ports import MotionDetector, SceneAnalyzer
from bandit.cameras.public import Camera, CameraStatus, CameraStatusChanged, FrameHub, GetCamera
from bandit.shared.events import EventBus

logger = logging.getLogger(__name__)


class AnalysisSupervisor:
    def __init__(
        self,
        frames: FrameHub,
        get_camera: GetCamera,
        analyzer: SceneAnalyzer,
        motion: MotionDetector,
        budget: DailyBudget,
        concurrency: int,
        bus: EventBus,
        policy: AnalysisPolicy,
    ) -> None:
        self._frames = frames
        self._get_camera = get_camera
        self._analyzer = analyzer
        self._motion = motion
        self._budget = budget
        self._limiter = asyncio.Semaphore(concurrency)
        self._bus = bus
        self._policy = policy
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
        analysis = CameraAnalysis(
            camera,
            self._analyzer,
            self._motion,
            self._budget,
            self._limiter,
            self._bus,
            self._policy,
        )
        subscription = self._frames.subscribe(camera.id)
        try:
            async for frame in subscription:
                await analysis.on_frame(frame)
        finally:
            self._frames.unsubscribe(camera.id, subscription)
