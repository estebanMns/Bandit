"""Tope diario de llamadas al modelo, para controlar el costo."""

from datetime import date

from bandit.shared.clock import Clock


class DailyBudget:
    def __init__(self, limit: int, clock: Clock) -> None:
        self._limit = limit
        self._clock = clock
        self._day: date | None = None
        self._used = 0

    def try_spend(self) -> bool:
        today = self._clock.now().date()
        if today != self._day:
            self._day = today
            self._used = 0
        if self._used >= self._limit:
            return False
        self._used += 1
        return True
