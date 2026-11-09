"""Fuente de fotogramas RTSP o HLS con ffmpeg como subproceso asíncrono."""

import asyncio
from collections.abc import AsyncIterator

from bandit.cameras.infrastructure.jpeg_parser import JpegStreamParser

_CHUNK_BYTES = 64 * 1024
_READ_TIMEOUT_SECONDS = 15


class FfmpegFrameSource:
    def __init__(self, ffmpeg_path: str, fps: int, width: int) -> None:
        self._ffmpeg_path = ffmpeg_path
        self._fps = fps
        self._width = width

    def _arguments(self, url: str) -> list[str]:
        # TCP evita fotogramas rotos en RTSP; HLS ya viaja por HTTP.
        transport = ["-rtsp_transport", "tcp"] if url.lower().startswith("rtsp") else []
        return [
            "-hide_banner",
            "-loglevel",
            "error",
            *transport,
            "-i",
            url,
            "-an",
            "-vf",
            f"fps={self._fps},scale={self._width}:-2",
            "-f",
            "image2pipe",
            "-c:v",
            "mjpeg",
            "-q:v",
            "6",
            "pipe:1",
        ]

    async def stream(self, url: str) -> AsyncIterator[bytes]:
        process = await asyncio.create_subprocess_exec(
            self._ffmpeg_path,
            *self._arguments(url),
            stdout=asyncio.subprocess.PIPE,
            # ffmpeg puede imprimir la URL con credenciales: su salida no se conserva.
            stderr=asyncio.subprocess.DEVNULL,
        )
        assert process.stdout is not None
        parser = JpegStreamParser()
        try:
            while True:
                chunk = await asyncio.wait_for(
                    process.stdout.read(_CHUNK_BYTES), _READ_TIMEOUT_SECONDS
                )
                if not chunk:
                    return
                for jpeg in parser.feed(chunk):
                    yield jpeg
        finally:
            if process.returncode is None:
                process.kill()
            await process.wait()
