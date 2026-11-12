"""La prueba con fotos usa el análisis real: sin confirmación no hay alerta."""

from uuid import uuid4

from bandit.analysis.domain.models import SceneAssessment, Severity, SituationType
from bandit.tools.simulate_alert import TEST_CAMERA_NAME, photo_camera_id, simulate

WEAPON = SceneAssessment(
    SituationType.WEAPON, Severity.HIGH, 0.9, "Persona con un arma en la mano."
)
CALM = SceneAssessment.calm()


class Analyzer:
    def __init__(self, *answers):
        self.answers = list(answers)

    async def assess(self, jpeg):
        return self.answers.pop(0)


async def run(*answers):
    created = []

    async def record(event):
        created.append(event)

    local = uuid4()
    frames = [(f"foto{i}.jpg", b"jpeg") for i in range(len(answers))]
    reports = await simulate(frames, local, Analyzer(*answers), record)
    return local, reports, created


async def test_two_weapon_photos_create_one_alert_on_the_test_camera():
    local, reports, created = await run(WEAPON, WEAPON)

    assert len(created) == 1
    assert created[0].camera_name == TEST_CAMERA_NAME
    assert created[0].camera_id == photo_camera_id(local)
    assert [r.alerted for r in reports] == [False, True]
    assert reports[0].name == "foto0.jpg"


async def test_calm_photos_never_alert():
    _, reports, created = await run(CALM, CALM, CALM)

    assert created == []
    assert {r.situation for r in reports} == {"none"}


async def test_a_single_detection_is_not_enough():
    _, _, created = await run(WEAPON, CALM, WEAPON)

    assert created == []
