"""Resumen de errores apto para registros y pantallas."""


def describe_error(error: BaseException) -> str:
    """Resumen seguro de un error para registros y pantallas: tipo, código y estado.

    Nunca incluye claves: los errores de Gemini no las repiten y aquí no se agregan URLs.
    """
    parts = [type(error).__name__]
    for attribute in ("code", "status"):
        value = getattr(error, attribute, None)
        if value not in (None, ""):
            parts.append(str(value))
    message = getattr(error, "message", None)
    if isinstance(message, str) and message:
        parts.append(message[:120])
    return " ".join(parts)[:300]
