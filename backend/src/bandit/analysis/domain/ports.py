"""Puertos del módulo de análisis."""

from typing import Protocol

from bandit.analysis.domain.models import SceneAssessment


class SceneAnalyzer(Protocol):
    async def assess(self, jpeg: bytes) -> SceneAssessment: ...


class MotionDetector(Protocol):
    def score(self, previous_jpeg: bytes, current_jpeg: bytes) -> float:
        """Fracción de cambio entre dos imágenes, de 0 a 1."""
        ...
