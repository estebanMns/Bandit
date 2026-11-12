"""La demostración solo compara las fotos del usuario y alerta en consola, nada más."""

from bandit.tools.face_demo import MATCH_THRESHOLD, _Verdict, run_demo


class Comparer:
    def __init__(self, *verdicts):
        self.verdicts = list(verdicts)
        self.calls = []

    async def compare(self, references, probe):
        self.calls.append(len(references))
        verdict = self.verdicts.pop(0)
        if isinstance(verdict, Exception):
            raise verdict
        return verdict


async def test_alerts_only_on_a_confident_match():
    comparer = Comparer(
        _Verdict(same_person=True, confidence=0.95, explanation="Mismos rasgos."),
        _Verdict(same_person=True, confidence=MATCH_THRESHOLD - 0.1, explanation="Dudoso."),
        _Verdict(same_person=False, confidence=0.9, explanation="Otra persona."),
    )
    probes = [("a.jpg", b"1"), ("b.jpg", b"2"), ("c.jpg", b"3")]

    results = await run_demo([b"r1", b"r2", b"r3", b"r4"], probes, comparer)

    assert [r.alert for r in results] == [True, False, False]
    assert comparer.calls == [3, 3, 3]


async def test_a_failed_comparison_never_alerts():
    results = await run_demo([b"r"], [("a.jpg", b"1")], Comparer(RuntimeError("caído")))

    assert results[0].alert is False
    assert "RuntimeError" in results[0].explanation
