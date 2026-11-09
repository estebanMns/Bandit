"""La caché de sesiones acelera sin dejar pasar sesiones cerradas o vencidas."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from bandit.identity.application.session_cache import SessionCache
from bandit.identity.domain.models import Role, User

NOW = datetime(2026, 11, 8, 22, 0, tzinfo=UTC)


def user() -> User:
    return User(uuid4(), "dueno@example.com", "hash", Role.OWNER, uuid4())


def test_remembers_a_session_for_a_short_time() -> None:
    cache, owner = SessionCache(timedelta(seconds=30)), user()
    cache.put("token", owner, NOW + timedelta(hours=8), NOW)

    assert cache.get("token", NOW + timedelta(seconds=29)) == owner
    assert cache.get("token", NOW + timedelta(seconds=31)) is None


def test_never_outlives_the_session_itself() -> None:
    cache, owner = SessionCache(timedelta(seconds=30)), user()
    cache.put("token", owner, NOW + timedelta(seconds=5), NOW)

    assert cache.get("token", NOW + timedelta(seconds=6)) is None


def test_logout_and_user_removal_take_effect_at_once() -> None:
    cache, owner = SessionCache(), user()
    cache.put("uno", owner, NOW + timedelta(hours=8), NOW)
    cache.put("dos", owner, NOW + timedelta(hours=8), NOW)

    cache.forget("uno")
    assert cache.get("uno", NOW) is None
    cache.forget_user(owner.id)
    assert cache.get("dos", NOW) is None
