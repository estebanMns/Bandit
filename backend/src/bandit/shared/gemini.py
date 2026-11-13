"""Reintentos ante saturación de Gemini y respaldo entre modelos cuando uno se queda sin cuota."""

import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger(__name__)

QUOTA_EXHAUSTED = 429
REST_SECONDS = 600.0
T = TypeVar("T")

_TRANSIENT = [429, 500, 502, 503, 504]


def http_options(attempts: int, max_delay: float) -> types.HttpOptions:
    """Espera exponencial con variación aleatoria entre intentos."""
    return types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=attempts,
            initial_delay=2.0,
            max_delay=max_delay,
            exp_base=2.0,
            jitter=1.0,
            http_status_codes=_TRANSIENT,
        )
    )


def model_list(*groups: str) -> list[str]:
    """Une modelos (sueltos o separados por coma) en orden, sin vacíos ni repetidos."""
    models: list[str] = []
    for group in groups:
        for model in group.split(","):
            name = model.strip()
            if name and name not in models:
                models.append(name)
    return models


class ModelChain:
    """Modelos en orden de preferencia. El que se queda sin cuota descansa un rato y se usa el
    siguiente, así la IA no se apaga cuando se agota la cuota de un solo modelo."""

    def __init__(
        self,
        models: Sequence[str],
        rest_seconds: float = REST_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not models:
            raise ValueError("Hace falta al menos un modelo")
        self._models = list(models)
        self._rest = rest_seconds
        self._clock = clock
        self._resting_until: dict[str, float] = {}

    @property
    def models(self) -> list[str]:
        return list(self._models)

    def _available(self) -> list[str]:
        now = self._clock()
        ready = [m for m in self._models if self._resting_until.get(m, 0.0) <= now]
        # Si todos descansan, se prueban igual: la cuota pudo haberse renovado.
        return ready or list(self._models)

    @property
    def active(self) -> str:
        return self._available()[0]

    async def run(self, call: Callable[[str], Awaitable[T]]) -> T:
        last_error: genai_errors.APIError | None = None
        for model in self._available():
            try:
                return await call(model)
            except genai_errors.APIError as error:
                if error.code != QUOTA_EXHAUSTED:
                    raise
                logger.warning("%s sin cuota; se prueba el siguiente modelo", model)
                self._resting_until[model] = self._clock() + self._rest
                last_error = error
        assert last_error is not None
        raise last_error
