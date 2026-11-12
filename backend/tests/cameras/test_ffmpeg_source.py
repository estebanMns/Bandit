"""Si el equipo no puede abrir ffmpeg, el error lo explica sin mostrar la URL."""

import asyncio

import pytest

from bandit.cameras.domain.ports import FrameSourceUnavailableError
from bandit.cameras.infrastructure.ffmpeg_source import FfmpegFrameSource

URL = "rtsp://usuario:clave-secreta@192.168.1.10:554/stream"


async def first_frame(source: FfmpegFrameSource) -> bytes:
    async for jpeg in source.stream(URL):
        return jpeg
    return b""


async def test_missing_ffmpeg_is_explained_without_the_url():
    source = FfmpegFrameSource("ffmpeg-que-no-existe", fps=1, width=320)

    with pytest.raises(FrameSourceUnavailableError) as raised:
        await first_frame(source)

    assert "ffmpeg" in str(raised.value)
    assert "clave-secreta" not in str(raised.value)


async def test_an_event_loop_without_subprocesses_is_explained(monkeypatch):
    async def unsupported(*args, **kwargs):
        raise NotImplementedError

    monkeypatch.setattr(asyncio, "create_subprocess_exec", unsupported)

    with pytest.raises(FrameSourceUnavailableError, match="--reload") as raised:
        await first_frame(FfmpegFrameSource("ffmpeg", fps=1, width=320))

    assert "clave-secreta" not in str(raised.value)
