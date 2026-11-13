"""Si el equipo no puede abrir ffmpeg, el error lo explica sin mostrar la URL."""

import asyncio
import sys

import pytest

from bandit.cameras.domain.ports import FrameSourceUnavailableError
from bandit.cameras.infrastructure.ffmpeg_source import FfmpegFrameSource, no_video_reason

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


def test_a_private_camera_explains_that_an_internet_server_cannot_reach_it():
    reason = no_video_reason("rtsp://admin:clave-secreta@192.168.1.102:554/cam")

    assert "192.168.1.102" in reason
    assert "red privada" in reason
    assert "nube de Imou" in reason
    assert "clave-secreta" not in reason


def test_a_public_camera_asks_to_check_its_address():
    reason = no_video_reason("https://usuario:clave-secreta@cdn.ejemplo.com/vivo.m3u8")

    assert "revisa la dirección" in reason
    assert "clave-secreta" not in reason


async def test_ffmpeg_ending_without_frames_is_explained(tmp_path):
    # Un "ffmpeg" que termina enseguida sin imprimir nada, como cuando no alcanza la cámara.
    fake = tmp_path / "ffmpeg-falso.py"
    fake.write_text("import sys\nsys.exit(1)\n")

    source = FfmpegFrameSource(sys.executable, fps=1, width=320)
    source._arguments = lambda url: [str(fake)]  # type: ignore[method-assign]

    with pytest.raises(FrameSourceUnavailableError, match="red privada"):
        await first_frame(source)
