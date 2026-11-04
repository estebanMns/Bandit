import pytest
from pydantic import ValidationError

from bandit.analysis.domain.models import SituationType, mentions_identity
from bandit.analysis.infrastructure.gemini_analyzer import AssessmentSchema, parse_assessment


@pytest.mark.parametrize(
    "text",
    [
        "Dos personas forcejean junto a la barra.",
        "Una persona apunta con un arma al cajero.",
        "Hay humo cerca de la cocina.",
        "",
    ],
)
def test_situation_descriptions_are_allowed(text):
    assert not mentions_identity(text)


@pytest.mark.parametrize(
    "text",
    [
        "El hombre se llama Pedro.",
        "Parece ser un delincuente conocido.",
        "Podría ser el buscado.",
        "Persona identificada como sospechoso.",
        "Se observa a Juan Pérez junto a la barra.",
        "Alias El Mono entra al local.",
    ],
)
def test_identity_mentions_are_detected(text):
    assert mentions_identity(text)


def test_output_schema_has_no_identity_fields():
    assert set(AssessmentSchema.model_fields) == {"type", "severity", "confidence", "description"}


def test_parses_a_valid_model_response():
    assessment = parse_assessment(
        '{"type":"fight","severity":"high","confidence":0.9,"description":"Pelea en la barra."}'
    )

    assert assessment.type is SituationType.FIGHT


@pytest.mark.parametrize(
    "raw",
    [
        "no es json",
        '{"type":"person_match","severity":"high","confidence":0.9,"description":""}',
        '{"type":"fight","severity":"high","confidence":3,"description":""}',
    ],
)
def test_rejects_responses_outside_the_schema(raw):
    with pytest.raises(ValidationError):
        parse_assessment(raw)
