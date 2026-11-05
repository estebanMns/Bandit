"""Límite de intentos en una ventana de tiempo."""

from datetime import datetime, timedelta


class AttemptThrottle:
    def __init__(self, max_attempts: int = 5, window: timedelta = timedelta(minutes=5)) -> None:
        self._max_attempts = max_attempts
        self._window = window
        self._attempts: dict[str, list[datetime]] = {}

    def is_blocked(self, key: str, now: datetime) -> bool:
        recent = [at for at in self._attempts.get(key, []) if now - at < self._window]
        if recent:
            self._attempts[key] = recent
        else:
            self._attempts.pop(key, None)
        return len(recent) >= self._max_attempts

    def record(self, key: str, now: datetime) -> None:
        self._attempts.setdefault(key, []).append(now)

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)
