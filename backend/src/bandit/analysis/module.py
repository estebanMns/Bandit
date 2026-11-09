"""Composición del módulo de análisis."""

from bandit.analysis.application.activity import ActivityTracker
from bandit.analysis.application.budget import DailyBudget
from bandit.analysis.application.camera_analysis import AnalysisPolicy
from bandit.analysis.application.supervisor import AnalysisSupervisor
from bandit.analysis.domain.models import AnalysisActivity
from bandit.analysis.domain.ports import SceneAnalyzer
from bandit.analysis.infrastructure.pillow_motion import PillowMotionDetector
from bandit.cameras.public import FrameHub, GetCamera
from bandit.shared.clock import Clock
from bandit.shared.config import Settings
from bandit.shared.events import EventBus


class AnalysisModule:
    def __init__(
        self,
        frames: FrameHub,
        get_camera: GetCamera,
        analyzer: SceneAnalyzer,
        settings: Settings,
        bus: EventBus,
        clock: Clock,
    ) -> None:
        self.model_enabled = bool(settings.gemini_api_key)
        self.budget = DailyBudget(settings.analysis_daily_call_limit, clock)
        self.activity = ActivityTracker()
        bus.subscribe(AnalysisActivity, self.activity.record)
        self.supervisor = AnalysisSupervisor(
            frames,
            get_camera,
            analyzer,
            PillowMotionDetector(),
            self.budget,
            settings.gemini_max_concurrency,
            bus,
            AnalysisPolicy(
                min_interval_seconds=settings.analysis_min_interval_seconds,
                motion_threshold=settings.analysis_motion_threshold,
                confirmation_frames=settings.analysis_confirmation_frames,
                cooldown_seconds=settings.analysis_cooldown_seconds,
            ),
        )
