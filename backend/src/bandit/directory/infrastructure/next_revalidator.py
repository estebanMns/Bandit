"""Pide a Next.js regenerar las páginas ISR del directorio."""

import logging

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10


class NextRevalidator:
    def __init__(self, frontend_url: str, secret: str) -> None:
        self._url = f"{frontend_url}/revalidar"
        self._secret = secret

    async def revalidate(self) -> None:
        if not self._secret:
            return
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.post(self._url, headers={"x-revalidate": self._secret})
                response.raise_for_status()
        except httpx.HTTPError as error:
            # El directorio igual se actualizará con el vencimiento de ISR.
            logger.warning("No se pudo revalidar el sitio: %s", type(error).__name__)
