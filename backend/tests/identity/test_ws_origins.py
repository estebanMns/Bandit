"""Orígenes permitidos para WebSockets: exactos o un patrón seguro para las vistas previas."""

import pytest

from bandit.identity.api.ws_tickets import WsTickets

PREVIEWS = "https://*-esteban3345s.vercel.app"


def tickets(*origins: str) -> WsTickets:
    return WsTickets(list(origins))


def test_an_exact_origin_is_allowed_with_or_without_trailing_slash():
    allowed = tickets("https://bandit.vercel.app")

    assert allowed.allows("https://bandit.vercel.app")
    assert allowed.allows("https://bandit.vercel.app/")
    assert not allowed.allows("https://otro.vercel.app")


@pytest.mark.parametrize(
    "origin",
    [
        "https://proyectos-de-bandit-mo744m777-esteban3345s.vercel.app",
        "https://bandit-git-main-esteban3345s.vercel.app",
    ],
)
def test_a_preview_pattern_allows_every_preview_of_the_team(origin):
    assert tickets(PREVIEWS).allows(origin)


@pytest.mark.parametrize(
    "origin",
    [
        "http://bandit-abc-esteban3345s.vercel.app",  # sin https
        "https://bandit-abc-otroequipo.vercel.app",  # otro equipo
        "https://evil.com.bandit-esteban3345s.vercel.app",  # subdominio extra
        "https://bandit-esteban3345s.vercel.app.evil.com",  # dominio ajeno
    ],
)
def test_a_preview_pattern_rejects_lookalikes(origin):
    assert not tickets(PREVIEWS).allows(origin)


@pytest.mark.parametrize("pattern", ["https://*.vercel.app", "http://*-equipo.vercel.app", "*"])
def test_too_broad_or_insecure_patterns_allow_nothing(pattern):
    assert not tickets(pattern).allows("https://cualquiera-equipo.vercel.app")
