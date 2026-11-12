"""Composición de la prueba de rostros. Apagada salvo FACE_WATCH_ENABLED=true."""

from bandit.cameras.public import FrameHub, GetCamera
from bandit.faces.application.log import FaceLog
from bandit.faces.application.watcher import AlertGate, FacePolicy, FaceSupervisor
from bandit.faces.domain.models import DailyLimit, FaceCheckDone
from bandit.faces.domain.ports import FaceComparer, MotionDetector, WatchList
from bandit.shared.clock import Clock
from bandit.shared.events import EventBus


class FacesModule:
    def __init__(
        self,
        frames: FrameHub,
        get_camera: GetCamera,
        comparer: FaceComparer | None,
        watch_list: WatchList,
        motion: MotionDetector,
        policy: FacePolicy,
        cooldown_seconds: float,
        daily_limit: int,
        bus: EventBus,
        clock: Clock,
    ) -> None:
        self.enabled = comparer is not None
        self.model: str | None = getattr(comparer, "model", None)
        self.watch_list = watch_list
        self.limit = DailyLimit(daily_limit, clock)
        self.log = FaceLog()
        bus.subscribe(FaceCheckDone, self.log.record)
        self.supervisor = (
            FaceSupervisor(
                frames,
                get_camera,
                comparer,
                watch_list,
                motion,
                self.limit,
                bus,
                policy,
                AlertGate(cooldown_seconds),
            )
            if comparer is not None
            else None
        )
