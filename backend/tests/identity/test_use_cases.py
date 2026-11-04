from datetime import timedelta

import pytest

from bandit.identity.domain.models import Role
from bandit.identity.module import IdentityModule
from bandit.shared.errors import AuthenticationError, ConflictError, InvalidDataError

PASSWORD = "clave-segura-de-prueba"


@pytest.fixture
def module(sessions, clock) -> IdentityModule:
    return IdentityModule(sessions, clock, timedelta(hours=1), cookie_secure=False)


async def test_login_issues_a_session_that_authenticates(module):
    await module.register_user.execute("Ana@Example.com", PASSWORD, Role.OPERATOR)

    issued = await module.login.execute("ana@example.com", PASSWORD)

    user = await module.authenticate.execute(issued.token)
    assert user.email == "ana@example.com"


async def test_wrong_password_is_rejected(module):
    await module.register_user.execute("ana@example.com", PASSWORD, Role.OPERATOR)

    with pytest.raises(AuthenticationError):
        await module.login.execute("ana@example.com", "otra-clave-incorrecta")


async def test_unknown_email_gets_the_same_error_as_a_wrong_password(module):
    with pytest.raises(AuthenticationError, match="Correo o clave incorrectos"):
        await module.login.execute("nadie@example.com", PASSWORD)


async def test_repeated_failures_block_login_even_with_the_right_password(module):
    await module.register_user.execute("ana@example.com", PASSWORD, Role.OPERATOR)
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            await module.login.execute("ana@example.com", "otra-clave-incorrecta")

    with pytest.raises(AuthenticationError, match="Demasiados intentos"):
        await module.login.execute("ana@example.com", PASSWORD)


async def test_expired_session_is_rejected(module, clock):
    await module.register_user.execute("ana@example.com", PASSWORD, Role.OPERATOR)
    issued = await module.login.execute("ana@example.com", PASSWORD)

    clock.advance(hours=2)

    with pytest.raises(AuthenticationError, match="expiró"):
        await module.authenticate.execute(issued.token)


async def test_logout_invalidates_the_session(module):
    await module.register_user.execute("ana@example.com", PASSWORD, Role.OPERATOR)
    issued = await module.login.execute("ana@example.com", PASSWORD)

    await module.logout.execute(issued.token)

    with pytest.raises(AuthenticationError):
        await module.authenticate.execute(issued.token)


async def test_duplicate_email_is_rejected(module):
    await module.register_user.execute("ana@example.com", PASSWORD, Role.OPERATOR)

    with pytest.raises(ConflictError):
        await module.register_user.execute("ANA@example.com", PASSWORD, Role.ADMIN)


async def test_short_password_is_rejected(module):
    with pytest.raises(InvalidDataError):
        await module.register_user.execute("ana@example.com", "corta", Role.OPERATOR)


async def test_bootstrap_only_runs_on_an_empty_database(module):
    await module.bootstrap_admin.execute("admin@example.com", PASSWORD)
    await module.bootstrap_admin.execute("otro@example.com", PASSWORD)

    await module.login.execute("admin@example.com", PASSWORD)
    with pytest.raises(AuthenticationError):
        await module.login.execute("otro@example.com", PASSWORD)
