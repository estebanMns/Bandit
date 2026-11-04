"""Compara modelos Gemini con fotogramas reales antes de fijar la configuración.

Coloca imágenes JPEG en carpetas con el nombre de la situación esperada:

    evaluation/frames/none/*.jpg
    evaluation/frames/fight/*.jpg
    evaluation/frames/robbery/*.jpg

Luego ejecuta, desde backend/ y con GEMINI_API_KEY definida:

    python scripts/evaluate_model.py evaluation/frames
"""

import argparse
import asyncio
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from bandit.analysis.domain.models import SituationType
from bandit.analysis.infrastructure.gemini_analyzer import GeminiSceneAnalyzer

_PRICES_PER_MILLION = {
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.5-flash-lite": (0.30, 2.50),
}
_IMAGE_TOKENS = {"low": 280, "high": 1120}
_PROMPT_TOKENS = 250
_OUTPUT_TOKENS = 80
_NONE = SituationType.NONE.value


@dataclass
class Result:
    expected: str
    predicted: str
    seconds: float


def estimated_cost(model: str, resolution: str) -> float:
    """Sin tokens de thinking: es un piso, no el costo exacto."""
    input_price, output_price = _PRICES_PER_MILLION[model]
    input_tokens = _IMAGE_TOKENS[resolution] + _PROMPT_TOKENS
    return (input_tokens * input_price + _OUTPUT_TOKENS * output_price) / 1_000_000


def load_samples(root: Path) -> list[tuple[str, bytes]]:
    return [
        (folder.name, image.read_bytes())
        for folder in sorted(path for path in root.iterdir() if path.is_dir())
        for image in sorted(folder.glob("*.jpg"))
    ]


async def run(
    api_key: str, model: str, resolution: str, samples: list[tuple[str, bytes]]
) -> list[Result]:
    analyzer = GeminiSceneAnalyzer(api_key, model, resolution)
    results = []
    for expected, jpeg in samples:
        started = time.perf_counter()
        assessment = await analyzer.assess(jpeg)
        results.append(Result(expected, assessment.type.value, time.perf_counter() - started))
    return results


def report(model: str, resolution: str, results: list[Result]) -> None:
    calm = [result for result in results if result.expected == _NONE]
    risky = [result for result in results if result.expected != _NONE]
    false_positives = sum(result.predicted != _NONE for result in calm)
    hits = sum(result.predicted == result.expected for result in risky)
    latency = sum(result.seconds for result in results) / len(results)
    print(
        f"{model:24} {resolution:5} "
        f"aciertos {hits}/{len(risky)}  "
        f"falsos positivos {false_positives}/{len(calm)}  "
        f"latencia {latency:.2f} s  "
        f"costo mínimo US${estimated_cost(model, resolution):.5f}"
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", type=Path)
    arguments = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Define GEMINI_API_KEY antes de ejecutar la prueba.", file=sys.stderr)
        return 1
    samples = load_samples(arguments.frames)
    if not samples:
        print(f"No hay imágenes .jpg en {arguments.frames}.", file=sys.stderr)
        return 1

    for model in _PRICES_PER_MILLION:
        for resolution in _IMAGE_TOKENS:
            report(model, resolution, await run(api_key, model, resolution, samples))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
