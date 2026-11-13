"""La prueba de clave RTSP funciona como ffmpeg: reto y respuesta por la misma conexión."""

import asyncio
import hashlib
import re
import secrets

import pytest

from bandit.cameras.infrastructure.rtsp_probe import RtspProbe

PATH = "/cam/realmonitor?channel=1&subtype=1"
USER, PASSWORD, REALM = "admin", "L@ clave#1", "Login to camara"


def md5(text: str) -> str:
    return hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()


class FakeCamera:
    """Cámara estilo Dahua: el nonce vale solo en su conexión, ofrece Basic y Digest y pide qop."""

    def __init__(self, qop: bool = True) -> None:
        self.qop = qop
        self.authenticated_attempts = 0
        self.server: asyncio.Server | None = None

    async def __aenter__(self) -> int:
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        return self.server.sockets[0].getsockname()[1]

    async def __aexit__(self, *exc: object) -> None:
        assert self.server is not None
        self.server.close()
        await self.server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        nonce = secrets.token_hex(8)  # nuevo en cada conexión
        try:
            while True:
                request = (await reader.readuntil(b"\r\n\r\n")).decode()
                cseq = re.search(r"CSeq: (\d+)", request).group(1)
                auth = re.search(r"(?im)^Authorization: (.+)$", request)
                if auth is None:
                    qop = ', qop="auth"' if self.qop else ""
                    body = "sin permiso"
                    writer.write(
                        (
                            f"RTSP/1.0 401 Unauthorized\r\nCSeq: {cseq}\r\n"
                            f'WWW-Authenticate: Basic realm="{REALM}"\r\n'
                            f'WWW-Authenticate: Digest realm="{REALM}", nonce="{nonce}"{qop}\r\n'
                            f"Content-Length: {len(body)}\r\n\r\n{body}"
                        ).encode()
                    )
                else:
                    self.authenticated_attempts += 1
                    ok = self._valid(auth.group(1), nonce)
                    status = "200 OK" if ok else "401 Unauthorized"
                    writer.write(f"RTSP/1.0 {status}\r\nCSeq: {cseq}\r\n\r\n".encode())
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()

    def _valid(self, header: str, nonce: str) -> bool:
        if not header.startswith("Digest "):
            return False
        params = dict(re.findall(r'(\w+)="?([^",]*)"?', header))
        if params.get("nonce") != nonce:
            return False
        ha1 = md5(f"{USER}:{REALM}:{PASSWORD}")
        ha2 = md5(f"DESCRIBE:{params['uri']}")
        if self.qop:
            expected = md5(f"{ha1}:{nonce}:{params['nc']}:{params['cnonce']}:auth:{ha2}")
        else:
            expected = md5(f"{ha1}:{nonce}:{ha2}")
        return params.get("response") == expected


@pytest.mark.parametrize("qop", [True, False])
async def test_the_right_password_is_accepted_on_the_same_connection(qop):
    camera = FakeCamera(qop=qop)
    async with camera as port:
        status = await RtspProbe().describe("127.0.0.1", port, PATH, USER, PASSWORD)

    assert status == 200
    assert camera.authenticated_attempts == 1


async def test_a_wrong_password_is_rejected_after_a_single_attempt():
    camera = FakeCamera()
    async with camera as port:
        status = await RtspProbe().describe("127.0.0.1", port, PATH, USER, "otra")

    assert status == 401
    assert camera.authenticated_attempts == 1


async def test_a_closed_port_means_no_answer():
    camera = FakeCamera()
    async with camera as port:
        pass

    assert await RtspProbe().describe("127.0.0.1", port, PATH, USER, PASSWORD) == 0
