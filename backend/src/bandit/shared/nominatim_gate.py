"""Turno compartido para Nominatim: un pedido por segundo en todo el backend.

La política de uso de Nominatim pide como máximo un pedido por segundo por aplicación,
así que la geocodificación de locales y la búsqueda de CAI esperan el mismo turno.
https://operations.osmfoundation.org/policies/nominatim/
"""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

_MIN_INTERVAL_SECONDS = 1.1
_lock = asyncio.Lock()
_last = 0.0


@asynccontextmanager
async def nominatim_turn() -> AsyncIterator[None]:
    global _last
    async with _lock:
        wait = _MIN_INTERVAL_SECONDS - (time.monotonic() - _last)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            yield
        finally:
            _last = time.monotonic()
