"""Prueba una ruta RTSP con DESCRIBE y autenticación digest o básica. Nunca registra la clave.

El reto (401 + nonce) y la respuesta autenticada viajan por la MISMA conexión, como hace
ffmpeg: muchas cámaras (Dahua, Imou) atan el nonce a la conexión y rechazan una respuesta que
llega por otra, aunque la clave sea correcta.
"""

import asyncio
import base64
import hashlib
import re
import secrets
from urllib.parse import quote

_TIMEOUT = 5.0
_MAX_HEADER_BYTES = 16 * 1024
_MAX_BODY_BYTES = 64 * 1024
_STATUS = re.compile(r"RTSP/1\.0 (\d{3})")
_PARAM = re.compile(r'(\w+)=(?:"([^"]*)"|([^,\s]+))')
UNAUTHORIZED = 401


def _md5(text: str) -> str:
    return hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()


def _status(response: str) -> int:
    match = _STATUS.match(response)
    return int(match.group(1)) if match else 0


def _challenges(response: str) -> list[str]:
    """Valor de cada encabezado WWW-Authenticate (puede haber uno Basic y otro Digest)."""
    return [
        line.split(":", 1)[1].strip()
        for line in response.split("\r\n")
        if line.lower().startswith("www-authenticate:")
    ]


def _params(challenge: str) -> dict[str, str]:
    return {
        match.group(1).lower(): match.group(2) if match.group(2) is not None else match.group(3)
        for match in _PARAM.finditer(challenge)
    }


def digest_header(challenge: str, username: str, password: str, uri: str) -> str | None:
    """Respuesta Digest (RFC 2617, MD5) a un reto `Digest realm=…, nonce=…[, qop=…]`."""
    params = _params(challenge)
    realm, nonce = params.get("realm"), params.get("nonce")
    if realm is None or nonce is None:
        return None
    ha1 = _md5(f"{username}:{realm}:{password}")
    ha2 = _md5(f"DESCRIBE:{uri}")
    fields = [
        f'username="{username}"',
        f'realm="{realm}"',
        f'nonce="{nonce}"',
        f'uri="{uri}"',
    ]
    qops = [option.strip() for option in params.get("qop", "").split(",") if option.strip()]
    if "auth" in qops:
        nc, cnonce = "00000001", secrets.token_hex(8)
        response = _md5(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
        fields += ["qop=auth", f"nc={nc}", f'cnonce="{cnonce}"']
    else:
        response = _md5(f"{ha1}:{nonce}:{ha2}")
    fields.append(f'response="{response}"')
    if "opaque" in params:
        fields.append(f'opaque="{params["opaque"]}"')
    if "algorithm" in params:
        fields.append(f"algorithm={params['algorithm']}")
    return "Digest " + ", ".join(fields)


def authorization(response: str, username: str, password: str, uri: str) -> str | None:
    """Prefiere Digest; usa Basic solo si la cámara no ofrece Digest."""
    challenges = _challenges(response)
    for challenge in challenges:
        if challenge.lower().startswith("digest"):
            return digest_header(challenge, username, password, uri)
    if any(challenge.lower().startswith("basic") for challenge in challenges):
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {token}"
    return None


async def _read_response(reader: asyncio.StreamReader) -> str:
    """Lee una respuesta RTSP completa (encabezados y cuerpo) para dejar libre la conexión."""
    head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), _TIMEOUT)
    if len(head) > _MAX_HEADER_BYTES:
        raise OSError("Respuesta RTSP demasiado grande")
    text = head.decode(errors="replace")
    length = re.search(r"(?im)^content-length:\s*(\d+)", text)
    if length:
        size = min(int(length.group(1)), _MAX_BODY_BYTES)
        await asyncio.wait_for(reader.readexactly(size), _TIMEOUT)
    return text


class RtspProbe:
    async def describe(self, ip: str, port: int, path: str, username: str, password: str) -> int:
        """Código RTSP de DESCRIBE. 401 significa que la cámara rechazó la clave enviada."""
        uri = f"rtsp://{ip}:{port}{quote(path, safe='/?=&_.-~%')}"
        try:
            reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), _TIMEOUT)
        except (OSError, TimeoutError):
            return 0
        try:
            first = await self._request(reader, writer, uri, 1, None)
            if _status(first) != UNAUTHORIZED:
                return _status(first)
            auth = authorization(first, username, password, uri)
            if auth is None:
                return UNAUTHORIZED
            return _status(await self._request(reader, writer, uri, 2, auth))
        except (OSError, TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
            return 0
        finally:
            writer.close()
            await asyncio.gather(writer.wait_closed(), return_exceptions=True)

    @staticmethod
    async def _request(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        uri: str,
        cseq: int,
        auth: str | None,
    ) -> str:
        lines = [
            f"DESCRIBE {uri} RTSP/1.0",
            f"CSeq: {cseq}",
            "Accept: application/sdp",
            "User-Agent: Bandit",
        ]
        if auth:
            lines.append(f"Authorization: {auth}")
        writer.write(("\r\n".join(lines) + "\r\n\r\n").encode())
        await writer.drain()
        return await _read_response(reader)
