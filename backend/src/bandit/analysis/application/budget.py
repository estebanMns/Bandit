"""Tope diario de llamadas al modelo, para controlar el costo."""

from datetime import date

from bandit.shared.clock import Clock


class DailyBudget:
    def __init__(self, limit: int, clock: Clock) -> None:
        self._limit = limit
        self._clock = clock
        self._day: date | None = None
        self._used = 0

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def used(self) -> int:
        self._roll_day()
        return self._used

    def _roll_day(self) -> None:
        today = self._clock.now().date()
        if today != self._day:
            self._day = today
            self._used = 0

    def try_spend(self) -> bool:
        self._roll_day()
        if self._used >= self._limit:
            return False
        self._used += 1
        return True
