"""Mide cuánto se equivoca la prueba de rostros: falsas alertas y personas que se escapan.

Solo con fotos de personas que dieron su consentimiento, en una carpeta local que nunca se sube:

    <carpeta>/personas/<id>/referencia/*.jpg   hasta 3 fotos de referencia de esa persona
    <carpeta>/personas/<id>/prueba/*.jpg       otras fotos de la MISMA persona

Cada persona se compara con sus propias fotos de prueba (pares genuinos: ¿la reconoce?) y con
las de todas las demás (pares impostores: ¿alerta por alguien que no es?). Usa el mismo
comparador e instrucción que la prueba en vivo, con un solo modelo para no mezclar resultados.
No guarda nada en la base de datos, no crea alertas y no envía nada fuera de Gemini.

Uso, dentro del contenedor del backend:

    python -m bandit.tools.face_eval /app/var/rostros_eval [--repeticiones 3] [--limite 200]
"""

import argparse
import asyncio
import csv
import math
import sys
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from bandit.faces.domain.models import MATCH_THRESHOLD
from bandit.faces.domain.ports import FaceComparer
from bandit.tools.face_demo import load_images

THRESHOLDS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)
_MAX_REFERENCES = 3
_Z95 = 1.96


@dataclass(frozen=True, slots=True)
class Person:
    id: str
    references: tuple[bytes, ...]
    probes: tuple[tuple[str, bytes], ...]


@dataclass(frozen=True, slots=True)
class Pair:
    reference: str
    probe_person: str
    probe_name: str

    @property
    def genuine(self) -> bool:
        return self.reference == self.probe_person


@dataclass(frozen=True, slots=True)
class Trial:
    pair: Pair
    repetition: int
    face_visible: bool
    same_person: bool
    confidence: float
    explanation: str
    error: bool = False

    def alerts(self, threshold: float = MATCH_THRESHOLD) -> bool:
        """La misma regla que la prueba en vivo, con el umbral que se quiera probar."""
        return (
            not self.error
            and self.face_visible
            and self.same_person
            and self.confidence >= threshold
        )


@dataclass(frozen=True, slots=True)
class Rate:
    errors: int
    total: int

    @property
    def value(self) -> float:
        return self.errors / self.total if self.total else 0.0

    @property
    def upper95(self) -> float:
        """Peor caso creíble (Wilson, 95 %). Con 0 errores se acerca a la regla del 3: 3/N."""
        if not self.total:
            return 1.0
        n, p = self.total, self.value
        center = p + _Z95**2 / (2 * n)
        spread = _Z95 * math.sqrt(p * (1 - p) / n + _Z95**2 / (4 * n * n))
        return min(1.0, (center + spread) / (1 + _Z95**2 / n))


@dataclass(frozen=True, slots=True)
class ThresholdStats:
    threshold: float
    false_alerts: Rate
    misses: Rate


@dataclass(frozen=True, slots=True)
class Summary:
    by_threshold: list[ThresholdStats]
    genuine_without_face: int
    impostor_without_face: int
    failed_calls: int
    unstable: Rate
    worst_false_alerts: list[Trial]


def load_people(root: Path) -> list[Person]:
    folder = root / "personas"
    if not folder.is_dir():
        return []
    people = []
    for person in sorted(path for path in folder.iterdir() if path.is_dir()):
        references = tuple(image for _, image in load_images(person / "referencia"))
        probes = tuple(load_images(person / "prueba"))
        if references and probes:
            people.append(Person(person.name, references[:_MAX_REFERENCES], probes))
    return people


def build_pairs(people: Sequence[Person]) -> list[Pair]:
    return [
        Pair(reference.id, probe_owner.id, probe_name)
        for reference in people
        for probe_owner in people
        for probe_name, _ in probe_owner.probes
    ]


async def evaluate(
    people: Sequence[Person],
    comparer: FaceComparer,
    repetitions: int = 1,
    limit: int | None = None,
    pause: Callable[[], Awaitable[None]] | None = None,
    pairs: Sequence[Pair] | None = None,
) -> list[Trial]:
    """Compara cada par `repetitions` veces; un error de la IA se anota y no detiene la medición."""
    by_id = {person.id: person for person in people}
    probes = {(person.id, name): image for person in people for name, image in person.probes}
    trials: list[Trial] = []
    for pair in pairs if pairs is not None else build_pairs(people):
        for repetition in range(1, repetitions + 1):
            if limit is not None and len(trials) >= limit:
                return trials
            if pause is not None and trials:
                await pause()
            image = probes[(pair.probe_person, pair.probe_name)]
            try:
                verdict = await comparer.compare(by_id[pair.reference].references, image)
            except Exception as error:
                trials.append(
                    Trial(pair, repetition, False, False, 0.0, type(error).__name__, True)
                )
                continue
            trials.append(
                Trial(
                    pair,
                    repetition,
                    verdict.face_visible,
                    verdict.same_person,
                    verdict.confidence,
                    verdict.explanation,
                )
            )
    return trials


def summarize(trials: Sequence[Trial], thresholds: Sequence[float] = THRESHOLDS) -> Summary:
    answered = [trial for trial in trials if not trial.error]
    genuine = [trial for trial in answered if trial.pair.genuine]
    impostor = [trial for trial in answered if not trial.pair.genuine]
    # Si en un par genuino no se ve la cara, falló la captura, no el reconocimiento.
    genuine_seen = [trial for trial in genuine if trial.face_visible]
    stats = [
        ThresholdStats(
            threshold,
            Rate(sum(trial.alerts(threshold) for trial in impostor), len(impostor)),
            Rate(sum(not trial.alerts(threshold) for trial in genuine_seen), len(genuine_seen)),
        )
        for threshold in thresholds
    ]
    decisions: dict[Pair, list[bool]] = {}
    for trial in answered:
        decisions.setdefault(trial.pair, []).append(trial.alerts())
    repeated = [answers for answers in decisions.values() if len(answers) > 1]
    worst = sorted(
        (trial for trial in impostor if trial.face_visible and trial.same_person),
        key=lambda trial: trial.confidence,
        reverse=True,
    )[:10]
    return Summary(
        stats,
        sum(not trial.face_visible for trial in genuine),
        sum(not trial.face_visible for trial in impostor),
        len(trials) - len(answered),
        Rate(sum(len(set(answers)) > 1 for answers in repeated), len(repeated)),
        worst,
    )


def write_csv(path: Path, trials: Sequence[Trial]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "persona_referencia",
                "persona_foto",
                "foto",
                "genuino",
                "repeticion",
                "error",
                "cara_visible",
                "misma_persona",
                "confianza",
                f"alerta_{MATCH_THRESHOLD:g}",
                "explicacion",
            ]
        )
        for trial in trials:
            writer.writerow(
                [
                    trial.pair.reference,
                    trial.pair.probe_person,
                    trial.pair.probe_name,
                    trial.pair.genuine,
                    trial.repetition,
                    trial.error,
                    trial.face_visible,
                    trial.same_person,
                    f"{trial.confidence:.2f}",
                    trial.alerts(),
                    trial.explanation,
                ]
            )


def _percent(rate: Rate) -> str:
    if not rate.total:
        return "     sin datos     "
    return f"{rate.value:6.1%} ({rate.errors}/{rate.total}, peor caso {rate.upper95:.1%})"


def print_summary(summary: Summary) -> None:
    print("Umbral | Falsas alertas (persona distinta) | Se escapa (persona correcta)")
    for stats in summary.by_threshold:
        mark = "  <- el de hoy" if math.isclose(stats.threshold, MATCH_THRESHOLD) else ""
        print(
            f" {stats.threshold:.2f}  | {_percent(stats.false_alerts):33} | "
            f"{_percent(stats.misses)}{mark}"
        )
    print(
        f"\nSin cara visible: {summary.genuine_without_face} pares genuinos (fallo de captura) y "
        f"{summary.impostor_without_face} impostores. Llamadas fallidas: {summary.failed_calls}."
    )
    if summary.unstable.total:
        print(
            f"Inestable (la misma foto cambia de decisión al repetir): {_percent(summary.unstable)}"
        )
    if summary.worst_false_alerts:
        print("\nPersonas distintas que el modelo dio por iguales (revisar a mano):")
        for trial in summary.worst_false_alerts:
            pair = trial.pair
            print(
                f"  {trial.confidence:.0%} ref={pair.reference} foto={pair.probe_person}/"
                f"{pair.probe_name} · {trial.explanation}"
            )
    print(
        "\n'Peor caso' es el límite superior al 95 %: con pocas comparaciones es alto aunque no "
        "haya errores. Para afirmar menos de 1 % de falsas alertas hacen falta unas 300 "
        "comparaciones impostoras sin errores."
    )


async def _main(root: Path, repetitions: int, limit: int | None, wait: float, model: str) -> int:
    from bandit.faces.infrastructure.gemini_comparer import GeminiFaceComparer
    from bandit.shared.config import get_settings

    settings = get_settings()
    if not settings.gemini_api_key:
        print("Falta GEMINI_API_KEY.")
        return 1
    people = load_people(root)
    if len(people) < 2:
        print(f"Hacen falta al menos 2 personas con referencia/ y prueba/ en {root / 'personas'}.")
        return 1
    model = model or settings.face_watch_model
    pairs = build_pairs(people)
    genuine = sum(pair.genuine for pair in pairs)
    calls = len(pairs) * repetitions if limit is None else min(limit, len(pairs) * repetitions)
    print(
        f"{len(people)} personas · {genuine} pares genuinos · {len(pairs) - genuine} impostores · "
        f"{repetitions} repeticiones · {calls} llamadas a {model}.\n"
    )

    async def pause() -> None:
        await asyncio.sleep(wait)

    trials = await evaluate(
        people, GeminiFaceComparer(settings.gemini_api_key, [model]), repetitions, limit, pause
    )
    output = root / "resultados.csv"
    write_csv(output, trials)
    print_summary(summarize(trials))
    print(f"\nDetalle por comparación en {output}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path, help="Carpeta con personas/<id>/referencia y prueba")
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument("--limite", type=int, help="Máximo de llamadas a Gemini")
    parser.add_argument("--pausa", type=float, default=1.0, help="Segundos entre llamadas")
    parser.add_argument("--modelo", default="", help="Por defecto FACE_WATCH_MODEL")
    args = parser.parse_args()
    sys.exit(asyncio.run(_main(args.root, args.repeticiones, args.limite, args.pausa, args.modelo)))


if __name__ == "__main__":
    main()
