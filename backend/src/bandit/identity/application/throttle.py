"""Límite de intentos fallidos de inicio de sesión."""

from datetime import datetime, timedelta


class LoginThrottle:
    def __init__(self, max_failures: int = 5, window: timedelta = timedelta(minutes=5)) -> None:
        self._max_failures = max_failures
        self._window = window
        self._failures: dict[str, list[datetime]] = {}

    def is_blocked(self, key: str, now: datetime) -> bool:
        recent = [at for at in self._failures.get(key, []) if now - at < self._window]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return len(recent) >= self._max_failures

    def record_failure(self, key: str, now: datetime) -> None:
        self._failures.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
