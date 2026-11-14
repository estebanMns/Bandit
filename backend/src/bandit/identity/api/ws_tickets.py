"""Tickets cortos para abrir WebSockets desde otro dominio.

Cuando el frontend vive en otro dominio (por ejemplo Vercel) el navegador no envía la
cookie de sesión al abrir el WebSocket contra el backend. El frontend pide entonces un
ticket por /api/auth/ws-ticket (misma cookie, vía el proxy del frontend) y lo pasa en la
URL del WebSocket. El ticket cifra el token de sesión y caduca en segundos.
"""

import re
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken

TICKET_TTL_SECONDS = 60


class WsTickets:
    def __init__(self, allowed_origins: list[str], key: bytes | None = None) -> None:
        # Clave por proceso: los tickets duran segundos y no necesitan sobrevivir reinicios.
        self._fernet = Fernet(key or Fernet.generate_key())
        self.allowed_origins = {origin.rstrip("/") for origin in allowed_origins if origin}

    def allows(self, origin: str) -> bool:
        """Origen exacto, o un patrón como https://*-equipo.vercel.app (vistas previas)."""
        origin = origin.rstrip("/")
        return any(
            origin == allowed or (_is_pattern(allowed) and _matches(origin, allowed))
            for allowed in self.allowed_origins
        )

    def issue(self, session_token: str) -> str:
        return self._fernet.encrypt(session_token.encode()).decode()

    def redeem(self, ticket: str) -> str | None:
        try:
            return self._fernet.decrypt(ticket.encode(), ttl=TICKET_TTL_SECONDS).decode()
        except (InvalidToken, ValueError):
            return None


_LABEL = "[a-z0-9-]+"


def _is_pattern(allowed: str) -> bool:
    """Un comodín solo vale en la primera parte del dominio y junto a texto fijo.

    `https://*-equipo.vercel.app` sí; `https://*.vercel.app` no: abriría la puerta a cualquier
    proyecto de Vercel. Siempre exige https.
    """
    parts = urlsplit(allowed)
    host = parts.netloc
    if parts.scheme != "https" or "*" not in host:
        return False
    first, _, rest = host.partition(".")
    return "*" not in rest and first != "*" and rest.count(".") >= 1


def _matches(origin: str, pattern: str) -> bool:
    parts = urlsplit(origin)
    if parts.scheme != "https":
        return False
    host_pattern = urlsplit(pattern).netloc
    regex = "".join(_LABEL if char == "*" else re.escape(char) for char in host_pattern)
    return re.fullmatch(regex, parts.netloc.lower()) is not None


def parse_origins(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]
