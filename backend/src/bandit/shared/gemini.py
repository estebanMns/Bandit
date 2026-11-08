"""Reintentos ante saturación de Gemini (429 y 5xx), que suelen durar segundos."""

from google.genai import types

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
