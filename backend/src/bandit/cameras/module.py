"""Composición del módulo de cámaras."""

from bandit.cameras.application.frame_hub import FrameHub
from bandit.cameras.application.supervisor import CaptureSupervisor
from bandit.cameras.application.use_cases import (
    GetCamera,
    ListCameras,
    RegisterCamera,
    RemoveCamera,
    SetCameraEnabled,
)
from bandit.cameras.domain.ports import FrameSource, UrlCipher
from bandit.cameras.infrastructure.repositories import SqlCameraRepository
from bandit.shared.clock import Clock
from bandit.shared.db import SessionFactory
from bandit.shared.events import EventBus


class CamerasModule:
    def __init__(
        self,
        sessions: SessionFactory,
        source: FrameSource,
        cipher: UrlCipher,
        bus: EventBus,
        clock: Clock,
    ) -> None:
        repository = SqlCameraRepository(sessions)
        self.frames = FrameHub()
        self.supervisor = CaptureSupervisor(repository, source, cipher, self.frames, bus, clock)
        self.register = RegisterCamera(repository, cipher, self.supervisor)
        self.get = GetCamera(repository)
        self.list_for = ListCameras(repository)
        self.set_enabled = SetCameraEnabled(repository, self.get, self.supervisor)
        self.remove = RemoveCamera(repository, self.get, self.supervisor)
