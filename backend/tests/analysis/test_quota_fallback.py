"""Si el modelo principal se queda sin cuota, el análisis sigue con el de respaldo."""

from types import SimpleNamespace

import pytest
from google.genai import errors

from bandit.analysis.domain.models import SituationType
from bandit.analysis.infrastructure.gemini_analyzer import GeminiSceneAnalyzer

CALM = '{"type": "none", "severity": "low", "confidence": 0.9, "description": ""}'


class Models:
    def __init__(self, exhausted: set[str]):
        self.exhausted = exhausted
        self.used: list[str] = []

    async def generate_content(self, model, contents, config):
        self.used.append(model)
        if model in self.exhausted:
            raise errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}})
        return SimpleNamespace(text=CALM)


def analyzer(models: Models, fallback: str = "respaldo") -> GeminiSceneAnalyzer:
    instance = GeminiSceneAnalyzer("clave", "principal", "low", fallback_model=fallback)
    instance._client = SimpleNamespace(aio=SimpleNamespace(models=models))  # type: ignore[assignment]
    return instance


async def test_switches_to_the_fallback_and_stays_there_for_a_while():
    models = Models(exhausted={"principal"})
    scene = analyzer(models)

    first = await scene.assess(b"jpeg")
    await scene.assess(b"jpeg")

    assert first.type is SituationType.NONE
    assert models.used == ["principal", "respaldo", "respaldo"]
    assert scene.active_model == "respaldo"


async def test_without_fallback_the_quota_error_is_raised():
    scene = analyzer(Models(exhausted={"principal"}), fallback="")

    with pytest.raises(errors.ClientError):
        await scene.assess(b"jpeg")
