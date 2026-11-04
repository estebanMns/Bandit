"""Descarga respetuosa: dominio permitido, robots.txt y una petición cada dos segundos."""

import asyncio
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

_ALLOWED_HOST = "www.policia.gov.co"
_ALLOWED_PATH_PREFIXES = ("/los-mas-buscados-colombia", "/sites/default/files/")
_ROBOTS_URL = f"https://{_ALLOWED_HOST}/robots.txt"
_USER_AGENT = "BanditDirectoryBot/0.1"
_MIN_INTERVAL_SECONDS = 2.0
_TIMEOUT_SECONDS = 30


class DisallowedUrlError(Exception):
    pass


class PoliteFetcher:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        min_interval: float = _MIN_INTERVAL_SECONDS,
    ) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=_TIMEOUT_SECONDS,
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=False,
        )
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last_request = 0.0
        self._robots: RobotFileParser | None = None

    async def _rules(self) -> RobotFileParser:
        if self._robots is None:
            response = await self._client.get(_ROBOTS_URL)
            response.raise_for_status()
            parser = RobotFileParser()
            parser.parse(response.text.splitlines())
            self._robots = parser
        return self._robots

    async def _ensure_allowed(self, url: str) -> None:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.hostname != _ALLOWED_HOST
            or not parts.path.startswith(_ALLOWED_PATH_PREFIXES)
        ):
            raise DisallowedUrlError(url)
        if not (await self._rules()).can_fetch(_USER_AGENT, url):
            raise DisallowedUrlError(url)

    async def _wait_turn(self) -> None:
        async with self._lock:
            elapsed = time.monotonic() - self._last_request
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_request = time.monotonic()

    async def fetch_text(self, url: str) -> str:
        await self._ensure_allowed(url)
        await self._wait_turn()
        response = await self._client.get(url)
        response.raise_for_status()
        return response.text

    async def fetch_bytes(self, url: str, max_bytes: int) -> bytes:
        await self._ensure_allowed(url)
        await self._wait_turn()
        content = bytearray()
        async with self._client.stream("GET", url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise ValueError("El archivo supera el tamaño permitido")
        return bytes(content)
