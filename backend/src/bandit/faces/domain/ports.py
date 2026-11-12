from collections.abc import Sequence
from typing import Protocol

from bandit.faces.domain.models import FaceVerdict, WatchedPerson


class FaceComparer(Protocol):
    async def compare(self, references: Sequence[bytes], probe: bytes) -> FaceVerdict: ...


class WatchList(Protocol):
    async def people(self) -> list[WatchedPerson]: ...


class MotionDetector(Protocol):
    def score(self, previous_jpeg: bytes, current_jpeg: bytes) -> float: ...
