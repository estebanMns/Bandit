"""Composición del módulo de cámaras."""

from datetime import timedelta

from bandit.cameras.application.discovery import ConnectDevice, PathAdvisor, ScanNetwork
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
from bandit.cameras.infrastructure.lan_scanner import LanScanner
from bandit.cameras.infrastructure.repositories import SqlCameraRepository
from bandit.cameras.infrastructure.rtsp_probe import RtspProbe
from bandit.shared.clock import Clock
from bandit.shared.db import SessionFactory
from bandit.shared.events import EventBus

SCAN_GAP = timedelta(minutes=2)


class CamerasModule:
    def __init__(
        self,
        sessions: SessionFactory,
        source: FrameSource,
        cipher: UrlCipher,
        bus: EventBus,
        clock: Clock,
        advisor: PathAdvisor,
    ) -> None:
        repository = SqlCameraRepository(sessions)
        self.frames = FrameHub()
        self.supervisor = CaptureSupervisor(repository, source, cipher, self.frames, bus, clock)
        self.register = RegisterCamera(repository, cipher, self.supervisor)
        self.get = GetCamera(repository)
        self.list_for = ListCameras(repository)
        self.set_enabled = SetCameraEnabled(repository, self.get, self.supervisor)
        self.remove = RemoveCamera(repository, self.get, self.supervisor)
        scanner = LanScanner()
        self.scan_network = ScanNetwork(scanner, clock, SCAN_GAP)
        self.connect_device = ConnectDevice(scanner, RtspProbe(), advisor)
