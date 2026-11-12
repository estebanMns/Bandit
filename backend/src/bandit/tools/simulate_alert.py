"""Prueba de punta a punta con fotos: Gemini real, regla de confirmación real e incidente real.

Pasa una carpeta de fotos JPEG por el mismo análisis que usan las cámaras. Si Gemini ve la
misma situación en fotos seguidas, se crea la alerta en el local indicado y aparece en
Eventos, el Monitor y el Panel. No envía WhatsApp: eso solo ocurre si un operador la confirma.

Bandit detecta situaciones, nunca identifica personas.

Uso, dentro del contenedor del backend:

    python -m bandit.tools.simulate_alert /app/var/pruebas/weapon --local "donpancho"
"""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid5

from bandit.analysis.application.budget import DailyBudget
from bandit.analysis.application.camera_analysis import AnalysisPolicy, CameraAnalysis
from bandit.analysis.domain.models import AnalysisActivity, SituationDetected
from bandit.analysis.domain.ports import SceneAnalyzer
from bandit.cameras.public import Camera, Frame
from bandit.shared.clock import SystemClock
from bandit.shared.events import InMemoryEventBus

TEST_CAMERA_NAME = "Prueba (fotos)"
_NAMESPACE = UUID("6d1c4c8e-5a0f-4b7e-9f0e-0b7a6f1d2c3a")
_EXTENSIONS = {".jpg", ".jpeg"}


def photo_camera_id(establishment_id: UUID) -> UUID:
    """Siempre la misma cámara de prueba por local, para reconocer sus alertas."""
    return uuid5(_NAMESPACE, f"prueba-fotos:{establishment_id}")


@dataclass(frozen=True, slots=True)
class FrameReport:
    name: str
    outcome: str
    situation: str
    confidence: float
    description: str
    alerted: bool


class _AlwaysMoving:
    """Las fotos son independientes: todas se analizan, sin filtro de movimiento."""

    def score(self, previous: bytes, current: bytes) -> float:
        return 1.0


def load_frames(folder: Path) -> list[tuple[str, bytes]]:
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in _EXTENSIONS)
    return [(path.name, path.read_bytes()) for path in files]


async def simulate(
    frames: list[tuple[str, bytes]],
    establishment_id: UUID,
    analyzer: SceneAnalyzer,
    record: Callable[[SituationDetected], Awaitable[object]],
    confirmation_frames: int = 2,
) -> list[FrameReport]:
    bus = InMemoryEventBus()
    reports: list[FrameReport] = []
    names = iter(name for name, _ in frames)

    async def on_activity(event: AnalysisActivity) -> None:
        assessment = event.assessment
        reports.append(
            FrameReport(
                name=next(names, "?"),
                outcome=event.outcome.value,
                situation=assessment.type.value if assessment else "-",
                confidence=assessment.confidence if assessment else 0.0,
                description=assessment.description if assessment else "",
                alerted=event.alerted,
            )
        )

    async def on_situation(event: SituationDetected) -> None:
        await record(event)

    bus.subscribe(AnalysisActivity, on_activity)
    bus.subscribe(SituationDetected, on_situation)
    camera = Camera(photo_camera_id(establishment_id), establishment_id, TEST_CAMERA_NAME, "")
    analysis = CameraAnalysis(
        camera,
        analyzer,
        _AlwaysMoving(),
        DailyBudget(len(frames) + 1, SystemClock()),
        asyncio.Semaphore(1),
        bus,
        AnalysisPolicy(
            min_interval_seconds=0,
            motion_threshold=0,
            confirmation_frames=confirmation_frames,
            cooldown_seconds=0,
        ),
    )
    start = datetime.now(UTC)
    for index, (_, jpeg) in enumerate(frames):
        await analysis.on_frame(Frame(camera.id, jpeg, start + timedelta(seconds=index * 3)))
    return reports


async def _main(folder: Path, local_name: str) -> int:
    from bandit.bootstrap import _scene_analyzer, build_application
    from bandit.shared.config import get_settings

    settings = get_settings()
    if not settings.gemini_api_key:
        print("Falta GEMINI_API_KEY: sin ella no hay análisis.")
        return 1
    frames = load_frames(folder)
    if not frames:
        print(f"No hay fotos .jpg en {folder}")
        return 1
    app = build_application(settings)
    try:
        locals_ = await app.establishments.list_all.execute()
        match = [item for item in locals_ if item.name.lower() == local_name.lower()]
        if not match:
            print("No existe ese local. Locales:", ", ".join(item.name for item in locals_))
            return 1
        created: list[object] = []

        async def record(event: SituationDetected) -> object:
            incident = await app.incidents.record_situation.execute(event)
            created.append(incident)
            return incident

        reports = await simulate(
            frames,
            match[0].id,
            _scene_analyzer(settings),
            record,
            settings.analysis_confirmation_frames,
        )
    finally:
        await app.engine.dispose()

    for report in reports:
        mark = "  <- ALERTA" if report.alerted else ""
        print(
            f"{report.name}: {report.outcome} · {report.situation} "
            f"({report.confidence:.0%}) {report.description}{mark}"
        )
    if created:
        print(
            f"\nSe creó {len(created)} alerta(s) en '{match[0].name}'. "
            "Revísala en Eventos o el Monitor."
        )
    else:
        print("\nNo se creó ninguna alerta: Gemini no vio la misma situación en fotos seguidas.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path, help="Carpeta con fotos .jpg en orden")
    parser.add_argument("--local", required=True, help="Nombre del local donde crear la alerta")
    args = parser.parse_args()
    sys.exit(asyncio.run(_main(args.folder, args.local)))


if __name__ == "__main__":
    main()
