"""Fuente que traduce las URL imou:// a su video HLS antes de leerlas con ffmpeg."""

from collections.abc import AsyncIterator
from urllib.parse import urlsplit

from bandit.cameras.domain.models import IMOU_SCHEME
from bandit.cameras.domain.ports import FrameSource
from bandit.cameras.infrastructure.imou_cloud import ImouCloudResolver


class ResolvingFrameSource:
    def __init__(self, inner: FrameSource, imou: ImouCloudResolver) -> None:
        self._inner = inner
        self._imou = imou

    async def stream(self, url: str) -> AsyncIterator[bytes]:
        # Se resuelve en cada conexión: si la URL de la nube caduca, la reconexión trae otra.
        if urlsplit(url).scheme.lower() == IMOU_SCHEME:
            url = await self._imou.resolve(url)
        async for jpeg in self._inner.stream(url):
            yield jpeg
