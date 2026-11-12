"""Memoria corta de las comparaciones, para la página Actividad. Nada se guarda en disco."""

from collections import Counter, deque
from dataclasses import dataclass, field
from uuid import UUID

from bandit.faces.domain.models import FaceCheck, FaceCheckDone, FaceOutcome

RECENT_LIMIT = 40


@dataclass(slots=True)
class EstablishmentFaces:
    recent: deque[FaceCheck] = field(default_factory=lambda: deque(maxlen=RECENT_LIMIT))
    counts: Counter[FaceOutcome] = field(default_factory=Counter)
    frames: dict[UUID, bytes] = field(default_factory=dict)


class FaceLog:
    def __init__(self) -> None:
        self._by_establishment: dict[UUID, EstablishmentFaces] = {}

    async def record(self, event: FaceCheckDone) -> None:
        check = event.check
        entry = self._by_establishment.setdefault(check.establishment_id, EstablishmentFaces())
        if len(entry.recent) == entry.recent.maxlen:
            entry.frames.pop(entry.recent[-1].id, None)
        entry.recent.appendleft(check)
        entry.counts[check.outcome] += 1
        entry.frames[check.id] = event.jpeg

    def for_establishment(self, establishment_id: UUID) -> EstablishmentFaces:
        return self._by_establishment.get(establishment_id, EstablishmentFaces())

    def frame(self, check_id: UUID) -> tuple[UUID, bytes] | None:
        for establishment_id, entry in self._by_establishment.items():
            if check_id in entry.frames:
                return establishment_id, entry.frames[check_id]
        return None
