"""La medición cuenta bien falsas alertas, personas que se escapan y respuestas inestables."""

import csv

from bandit.faces.domain.models import FaceVerdict
from bandit.tools.face_eval import (
    Pair,
    Person,
    Rate,
    Trial,
    build_pairs,
    evaluate,
    load_people,
    summarize,
    write_csv,
)


class ScriptedComparer:
    """Responde según (primera referencia, foto); así cada par tiene su respuesta."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = 0

    async def compare(self, references, probe):
        self.calls += 1
        answer = self.answers[(references[0], probe)]
        if isinstance(answer, list):
            answer = answer.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def verdict(same, confidence, visible=True):
    return FaceVerdict(visible, same, confidence, "explicación")


ANA = Person("ana", (b"ref-ana",), (("a1.jpg", b"foto-a1"),))
LUIS = Person("luis", (b"ref-luis",), (("l1.jpg", b"foto-l1"),))


def test_every_person_is_compared_with_everyone_elses_photos():
    pairs = build_pairs([ANA, LUIS])

    assert [(p.reference, p.probe_person, p.genuine) for p in pairs] == [
        ("ana", "ana", True),
        ("ana", "luis", False),
        ("luis", "ana", False),
        ("luis", "luis", True),
    ]


async def test_counts_false_alerts_and_misses_per_threshold():
    comparer = ScriptedComparer(
        {
            (b"ref-ana", b"foto-a1"): verdict(True, 0.95),
            (b"ref-ana", b"foto-l1"): verdict(True, 0.85),  # falsa alerta con umbral 0.8
            (b"ref-luis", b"foto-a1"): verdict(False, 0.9),
            (b"ref-luis", b"foto-l1"): verdict(True, 0.7),  # se escapa con umbral 0.8
        }
    )

    trials = await evaluate([ANA, LUIS], comparer)
    stats = {s.threshold: s for s in summarize(trials, (0.6, 0.8, 0.9)).by_threshold}

    assert (stats[0.8].false_alerts.errors, stats[0.8].false_alerts.total) == (1, 2)
    assert (stats[0.8].misses.errors, stats[0.8].misses.total) == (1, 2)
    assert stats[0.9].false_alerts.errors == 0
    assert stats[0.6].misses.errors == 0
    assert summarize(trials).worst_false_alerts[0].pair == Pair("ana", "luis", "l1.jpg")


async def test_no_face_in_a_genuine_pair_is_a_capture_failure_not_a_miss():
    comparer = ScriptedComparer(
        {
            (b"ref-ana", b"foto-a1"): verdict(False, 0.1, visible=False),
            (b"ref-ana", b"foto-l1"): verdict(False, 0.9),
            (b"ref-luis", b"foto-a1"): verdict(False, 0.9),
            (b"ref-luis", b"foto-l1"): verdict(True, 0.9),
        }
    )

    summary = summarize(await evaluate([ANA, LUIS], comparer))
    today = next(s for s in summary.by_threshold if s.threshold == 0.8)

    assert summary.genuine_without_face == 1
    assert (today.misses.errors, today.misses.total) == (0, 1)


async def test_a_failed_call_is_recorded_and_the_rest_keeps_going():
    comparer = ScriptedComparer(
        {
            (b"ref-ana", b"foto-a1"): RuntimeError("caído"),
            (b"ref-ana", b"foto-l1"): verdict(False, 0.9),
            (b"ref-luis", b"foto-a1"): verdict(False, 0.9),
            (b"ref-luis", b"foto-l1"): verdict(True, 0.9),
        }
    )

    trials = await evaluate([ANA, LUIS], comparer)
    summary = summarize(trials)

    assert len(trials) == 4
    assert summary.failed_calls == 1
    assert next(s for s in summary.by_threshold if s.threshold == 0.8).misses.total == 1


async def test_repetitions_reveal_unstable_answers_and_the_limit_caps_calls():
    comparer = ScriptedComparer(
        {
            (b"ref-ana", b"foto-a1"): [verdict(True, 0.9), verdict(True, 0.6)],
            (b"ref-ana", b"foto-l1"): [verdict(False, 0.9), verdict(False, 0.9)],
        }
    )
    pauses = []

    async def pause():
        pauses.append(1)

    trials = await evaluate([ANA, LUIS], comparer, repetitions=2, limit=4, pause=pause)
    summary = summarize(trials)

    assert comparer.calls == 4
    assert len(pauses) == 3
    assert (summary.unstable.errors, summary.unstable.total) == (1, 2)


def test_worst_case_with_no_errors_follows_the_rule_of_three():
    assert 0.009 < Rate(0, 300).upper95 < 0.013
    assert Rate(0, 0).upper95 == 1.0


def test_loads_only_complete_people_and_writes_one_row_per_comparison(tmp_path):
    for name in ("ana", "luis"):
        (tmp_path / "personas" / name / "referencia").mkdir(parents=True)
        (tmp_path / "personas" / name / "referencia" / "r.jpg").write_bytes(b"r")
        (tmp_path / "personas" / name / "prueba").mkdir()
        (tmp_path / "personas" / name / "prueba" / "p.jpg").write_bytes(b"p")
    (tmp_path / "personas" / "sin-pruebas" / "referencia").mkdir(parents=True)

    people = load_people(tmp_path)
    assert [person.id for person in people] == ["ana", "luis"]

    trials = [Trial(Pair("ana", "luis", "p.jpg"), 1, True, True, 0.91, "Se parecen")]
    write_csv(tmp_path / "resultados.csv", trials)
    rows = list(csv.DictReader((tmp_path / "resultados.csv").open(encoding="utf-8")))

    assert rows[0]["genuino"] == "False"
    assert rows[0]["alerta_0.8"] == "True"
    assert rows[0]["confianza"] == "0.91"
