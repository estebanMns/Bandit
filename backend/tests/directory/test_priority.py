"""El directorio se ordena con datos publicados por la Policía, sin calificar a las personas."""

from uuid import uuid4

import pytest

from bandit.directory.domain.models import WantedRecord, crime_level, parse_reward, priority_key


@pytest.mark.parametrize(
    ("text", "amount"),
    [
        ("10 millones", 10_000_000),
        ("Hasta $50 millones", 50_000_000),
        ("$200.000.000", 200_000_000),
        ("1,5 millones", 1_500_000),
        ("1.500 millones", 1_500_000_000),
        ("500 mil", 500_000),
        ("No Aplica", None),
        ("N/A", None),
        ("", None),
        (None, None),
    ],
)
def test_reads_the_published_reward(text, amount):
    assert parse_reward(text) == amount


@pytest.mark.parametrize(
    ("crime", "level"),
    [
        ("HOMICIDIOS", 0),
        ("Extorsión agravada", 1),
        ("Acceso carnal violento", 2),
        ("Tráfico de estupefacientes", 3),
        ("Hurto calificado", 4),
        ("Abuso de confianza", 5),
        (None, 5),
    ],
)
def test_crime_levels_follow_a_fixed_list(crime, level):
    assert crime_level(crime) == level


def record(name, reward=None, crime=None, position=None):
    return WantedRecord(
        id=uuid4(),
        slug=name.lower(),
        name=name,
        alias=None,
        crime=crime,
        reward=None,
        region=None,
        hotline_email=None,
        reward_amount=reward,
        listing_position=position,
    )


def test_highest_reward_first_then_gravest_crime_then_police_order():
    records = [
        record("Hurto sin recompensa", crime="Hurto", position=0),
        record("Homicidio sin recompensa", crime="Homicidio", position=5),
        record("Diez millones", reward=10_000_000, crime="Hurto", position=9),
        record("Cincuenta millones", reward=50_000_000, position=8),
        record("Homicidio primero en la página", crime="Homicidio", position=1),
    ]

    ordered = [item.name for item in sorted(records, key=priority_key)]

    assert ordered == [
        "Cincuenta millones",
        "Diez millones",
        "Homicidio primero en la página",
        "Homicidio sin recompensa",
        "Hurto sin recompensa",
    ]
