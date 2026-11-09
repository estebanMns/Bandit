"""Prueba una ruta RTSP con DESCRIBE y autenticación digest o básica. Nunca registra la clave."""

import asyncio
import base64
import hashlib
import re
from urllib.parse import quote

_TIMEOUT = 5.0
_STATUS = re.compile(r"RTSP/1\.0 (\d{3})")


def _status(response: str) -> int:
    match = _STATUS.match(response)
    return int(match.group(1)) if match else 0


def _digest(challenge: str, username: str, password: str, uri: str) -> str | None:
    realm = re.search(r'realm="([^"]*)"', challenge)
    nonce = re.search(r'nonce="([^"]*)"', challenge)
    if realm is None or nonce is None:
        return None
    ha1 = hashlib.md5(
        f"{username}:{realm.group(1)}:{password}".encode(), usedforsecurity=False
    ).hexdigest()
    ha2 = hashlib.md5(f"DESCRIBE:{uri}".encode(), usedforsecurity=False).hexdigest()
    response = hashlib.md5(
        f"{ha1}:{nonce.group(1)}:{ha2}".encode(), usedforsecurity=False
    ).hexdigest()
    return (
        f'Digest username="{username}", realm="{realm.group(1)}", '
        f'nonce="{nonce.group(1)}", uri="{uri}", response="{response}"'
    )


class RtspProbe:
    async def _send(self, ip: str, port: int, uri: str, auth: str | None) -> str:
        lines = [
            f"DESCRIBE {uri} RTSP/1.0",
            "CSeq: 2",
            "Accept: application/sdp",
            "User-Agent: Bandit",
        ]
        if auth:
            lines.append(f"Authorization: {auth}")
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), _TIMEOUT)
        try:
            writer.write(("\r\n".join(lines) + "\r\n\r\n").encode())
            await writer.drain()
            return (await asyncio.wait_for(reader.read(8192), _TIMEOUT)).decode(errors="replace")
        finally:
            writer.close()
            await asyncio.gather(writer.wait_closed(), return_exceptions=True)

    async def describe(self, ip: str, port: int, path: str, username: str, password: str) -> int:
        uri = f"rtsp://{ip}:{port}{quote(path, safe='/?=&_.-~%')}"
        try:
            reply = await self._send(ip, port, uri, None)
            if _status(reply) != 401:
                return _status(reply)
            if "digest" in reply.lower():
                auth = _digest(reply, username, password, uri)
            else:
                token = base64.b64encode(f"{username}:{password}".encode()).decode()
                auth = f"Basic {token}"
            return _status(await self._send(ip, port, uri, auth)) if auth else 401
        except (OSError, TimeoutError):
            return 0
