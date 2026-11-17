from collections.abc import Sequence
from typing import Protocol

from bandit.faces.domain.models import FaceVerdict, WatchedPerson


class FaceComparer(Protocol):
    async def compare(self, references: Sequence[bytes], probe: bytes) -> FaceVerdict: ...

    # Una sola consulta contra varios candidatos. Devuelve el índice del candidato o None.
    async def identify(
        self, candidates: Sequence[WatchedPerson], probe: bytes
    ) -> tuple[FaceVerdict, int | None]: ...


class WatchList(Protocol):
    async def people(self) -> list[WatchedPerson]: ...


class MotionDetector(Protocol):
    def score(self, previous_jpeg: bytes, current_jpeg: bytes) -> float: ...
