"""Separa JPEG completos de un flujo de bytes de ffmpeg."""

_START_OF_IMAGE = b"\xff\xd8"
_END_OF_IMAGE = b"\xff\xd9"


class JpegStreamParser:
    def __init__(self, max_buffer_bytes: int = 8 * 1024 * 1024) -> None:
        self._buffer = bytearray()
        self._max_buffer_bytes = max_buffer_bytes

    def feed(self, chunk: bytes) -> list[bytes]:
        self._buffer.extend(chunk)
        frames: list[bytes] = []
        while True:
            start = self._buffer.find(_START_OF_IMAGE)
            if start == -1:
                self._buffer.clear()
                return frames
            end = self._buffer.find(_END_OF_IMAGE, start + len(_START_OF_IMAGE))
            if end == -1:
                del self._buffer[:start]
                if len(self._buffer) > self._max_buffer_bytes:
                    self._buffer.clear()
                return frames
            stop = end + len(_END_OF_IMAGE)
            frames.append(bytes(self._buffer[start:stop]))
            del self._buffer[:stop]
