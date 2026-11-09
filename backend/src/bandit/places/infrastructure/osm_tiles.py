"""Mosaicos de OpenStreetMap servidos desde nuestro dominio, con caché en disco.

El sitio usa COEP require-corp, así que el navegador no carga imágenes de otros dominios
que no lo permitan. Se cumplen las reglas de uso de los mosaicos de OSM: User-Agent propio,
pocas descargas a la vez y caché local. https://operations.osmfoundation.org/policies/tiles/
"""

import asyncio
import logging
from pathlib import Path

import httpx

from bandit.shared.error_summary import describe_error

logger = logging.getLogger(__name__)

_PNG_SIGNATURE = b"\x89PNG"
_MAX_DOWNLOADS = 2


class CachedOsmTiles:
    def __init__(
        self,
        root: str,
        user_agent: str,
        url: str = "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._root = Path(root)
        self._user_agent = user_agent
        self._url = url
        self._transport = transport
        self._downloads = asyncio.Semaphore(_MAX_DOWNLOADS)

    def _path(self, z: int, x: int, y: int) -> Path:
        return self._root / str(z) / str(x) / f"{y}.png"

    async def fetch(self, z: int, x: int, y: int) -> bytes | None:
        path = self._path(z, x, y)
        if path.is_file():
            return path.read_bytes()
        async with self._downloads:
            try:
                async with httpx.AsyncClient(transport=self._transport, timeout=15) as client:
                    response = await client.get(
                        self._url.format(z=z, x=x, y=y), headers={"User-Agent": self._user_agent}
                    )
                response.raise_for_status()
            except httpx.HTTPError as error:
                logger.warning("No se pudo descargar un mosaico: %s", describe_error(error))
                return None
        tile = response.content
        if not tile.startswith(_PNG_SIGNATURE):
            return None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(tile)
        return tile
