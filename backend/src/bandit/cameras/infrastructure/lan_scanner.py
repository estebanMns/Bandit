"""Barrido TCP de la red local y lectura de cabeceras para adivinar la marca."""

import asyncio
import re
from collections.abc import Sequence

from bandit.cameras.domain.discovery import DiscoveredDevice

PORTS = (554, 8554, 80, 8000, 37777)
_CONNECT_TIMEOUT = 0.8
_READ_TIMEOUT = 2.5
_CONCURRENCY = 128

_BRANDS = (
    ("Dahua / Imou", ("dahua", "imou", "easy4ip", "lechange", "37777")),
    ("Hikvision / EZVIZ", ("hikvision", "ezviz", "dnvrs-webs", "app-webs")),
    ("TP-Link Tapo", ("tp-link", "tapo")),
    ("Reolink", ("reolink",)),
)
_TITLE = re.compile(r"<title>([^<]{0,80})</title>", re.IGNORECASE)


def guess_brand(*clues: str | None) -> str | None:
    text = " ".join(clue for clue in clues if clue).lower()
    for brand, words in _BRANDS:
        if any(word in text for word in words):
            return brand
    return None


async def _open(ip: str, port: int) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), _CONNECT_TIMEOUT)
    except (OSError, TimeoutError):
        return False
    writer.close()
    await asyncio.gather(writer.wait_closed(), return_exceptions=True)
    return True


async def _exchange(ip: str, port: int, request: bytes) -> str:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), _CONNECT_TIMEOUT)
    except (OSError, TimeoutError):
        return ""
    try:
        writer.write(request)
        await writer.drain()
        data = await asyncio.wait_for(reader.read(4096), _READ_TIMEOUT)
        return data.decode(errors="replace")
    except (OSError, TimeoutError):
        return ""
    finally:
        writer.close()
        await asyncio.gather(writer.wait_closed(), return_exceptions=True)


def _header(response: str, name: str) -> str | None:
    for line in response.splitlines():
        key, _, value = line.partition(":")
        if key.strip().lower() == name:
            return value.strip()[:120] or None
    return None


class LanScanner:
    async def scan(self, hosts: Sequence[str]) -> list[DiscoveredDevice]:
        limiter = asyncio.Semaphore(_CONCURRENCY)

        async def probe(ip: str, port: int) -> tuple[str, int] | None:
            async with limiter:
                return (ip, port) if await _open(ip, port) else None

        found = await asyncio.gather(*(probe(ip, port) for ip in hosts for port in PORTS))
        ports_by_host: dict[str, list[int]] = {}
        for hit in found:
            if hit is not None:
                ports_by_host.setdefault(hit[0], []).append(hit[1])
        devices = await asyncio.gather(
            *(self._describe(ip, tuple(sorted(ports))) for ip, ports in ports_by_host.items())
        )
        return list(devices)

    async def inspect(self, ip: str) -> DiscoveredDevice | None:
        open_ports = [port for port in PORTS if await _open(ip, port)]
        return await self._describe(ip, tuple(open_ports)) if open_ports else None

    async def _describe(self, ip: str, ports: tuple[int, ...]) -> DiscoveredDevice:
        rtsp_server = http_server = title = None
        rtsp_port = 554 if 554 in ports else 8554 if 8554 in ports else None
        if rtsp_port:
            reply = await _exchange(
                ip,
                rtsp_port,
                f"OPTIONS rtsp://{ip}:{rtsp_port}/ RTSP/1.0\r\nCSeq: 1\r\n\r\n".encode(),
            )
            rtsp_server = _header(reply, "server")
        if 80 in ports:
            reply = await _exchange(
                ip, 80, f"GET / HTTP/1.0\r\nHost: {ip}\r\nUser-Agent: Bandit\r\n\r\n".encode()
            )
            http_server = _header(reply, "server")
            match = _TITLE.search(reply)
            title = match.group(1).strip() if match else None
        clue_ports = "37777" if 37777 in ports else None
        return DiscoveredDevice(
            ip=ip,
            open_ports=ports,
            brand=guess_brand(rtsp_server, http_server, title, clue_ports),
            rtsp_server=rtsp_server,
            http_server=" · ".join(part for part in (http_server, title) if part) or None,
        )
