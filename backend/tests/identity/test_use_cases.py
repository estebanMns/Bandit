from datetime import timedelta
from uuid import UUID, uuid4

import pytest

from bandit.identity.domain.models import Role, User
from bandit.identity.infrastructure.repositories import SqlUserRepository
from bandit.identity.module import IdentityModule
from bandit.shared.errors import (
    AuthenticationError,
    ConflictError,
    InvalidDataError,
    RateLimitedError,
)

PASSWORD = "clave-segura-de-prueba"


class FakeLocals:
    def __init__(self) -> None:
        self.created: list[tuple[str, str]] = []

    async def create(self, name: str, address: str) -> UUID:
        self.created.append((name, address))
        return uuid4()


@pytest.fixture
def module(sessions, clock) -> IdentityModule:
    return IdentityModule(
        sessions, clock, timedelta(hours=1), cookie_secure=False, establishments=FakeLocals()
    )


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


async def test_sign_up_creates_an_owner_of_a_new_local(module):
    user = await module.sign_up.execute("Ana@Example.com", PASSWORD, "Bar", "Calle 1", "ip")

    assert user.role is Role.OWNER
    assert user.establishment_id is not None
    assert user.email == "ana@example.com"
    await module.login.execute("ana@example.com", PASSWORD)


async def test_rejected_sign_up_creates_no_local(sessions, clock):
    locals_ = FakeLocals()
    module = IdentityModule(
        sessions, clock, timedelta(hours=1), cookie_secure=False, establishments=locals_
    )
    await module.sign_up.execute("ana@example.com", PASSWORD, "Bar", "Calle 1", "ip")

    with pytest.raises(ConflictError):
        await module.sign_up.execute("ANA@example.com", PASSWORD, "Otro", "Calle 2", "ip")
    with pytest.raises(InvalidDataError):
        await module.sign_up.execute("beto@example.com", "corta", "Otro", "Calle 2", "ip")

    assert locals_.created == [("Bar", "Calle 1")]


async def test_sign_up_is_limited_per_client_but_not_globally(module):
    for number in range(5):
        await module.sign_up.execute(f"u{number}@example.com", PASSWORD, "Bar", "Calle", "ip-1")

    with pytest.raises(RateLimitedError):
        await module.sign_up.execute("u9@example.com", PASSWORD, "Bar", "Calle", "ip-1")

    await module.sign_up.execute("u9@example.com", PASSWORD, "Bar", "Calle", "ip-2")


async def test_sign_up_limit_expires(module, clock):
    for number in range(5):
        await module.sign_up.execute(f"u{number}@example.com", PASSWORD, "Bar", "Calle", "ip")

    clock.advance(hours=2)

    await module.sign_up.execute("u9@example.com", PASSWORD, "Bar", "Calle", "ip")


async def test_duplicate_email_from_a_race_is_a_conflict(sessions):
    users = SqlUserRepository(sessions)
    await users.add(User(uuid4(), "ana@example.com", "hash", Role.OWNER))

    with pytest.raises(ConflictError):
        await users.add(User(uuid4(), "ana@example.com", "hash", Role.OWNER))
