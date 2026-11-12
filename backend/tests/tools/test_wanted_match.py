"""La prueba de persona buscada crea una sola alerta, y solo con una coincidencia segura."""

from bandit.tools.face_demo import _Verdict
from bandit.tools.wanted_match import MATCH_THRESHOLD, describe_match, watch


class Comparer:
    def __init__(self, *verdicts):
        self.verdicts = list(verdicts)

    async def compare(self, references, probe):
        verdict = self.verdicts.pop(0)
        if isinstance(verdict, Exception):
            raise verdict
        return verdict


async def probes(*names):
    for name in names:
        yield name, name.encode()


async def test_only_the_first_confident_match_creates_an_alert():
    matches = []

    async def on_match(name, jpeg, confidence, explanation):
        matches.append((name, confidence))

    comparer = Comparer(
        _Verdict(same_person=True, confidence=MATCH_THRESHOLD - 0.1, explanation="Dudoso."),
        _Verdict(same_person=True, confidence=0.95, explanation="Mismos rasgos."),
        _Verdict(same_person=True, confidence=0.99, explanation="Mismos rasgos."),
    )

    reports = await watch(probes("a", "b", "c"), [b"r"], comparer, on_match)

    assert matches == [("b", 0.95)]
    assert [r.alerted for r in reports] == [False, True, False]


async def test_another_person_or_a_failure_never_alerts():
    async def on_match(*args):
        raise AssertionError("no debía alertar")

    comparer = Comparer(
        _Verdict(same_person=False, confidence=0.99, explanation="Otra persona."),
        RuntimeError("caído"),
    )

    reports = await watch(probes("a", "b"), [b"r"], comparer, on_match)

    assert [r.alerted for r in reports] == [False, False]


def test_the_description_says_it_is_a_test_and_fits_the_column():
    text = describe_match("Persona Prueba", 0.95, "x" * 500)

    assert "registro de prueba" in text
    assert len(text) <= 300
