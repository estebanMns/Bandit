"""Tickets cortos para abrir WebSockets desde otro dominio.

Cuando el frontend vive en otro dominio (por ejemplo Vercel) el navegador no envía la
cookie de sesión al abrir el WebSocket contra el backend. El frontend pide entonces un
ticket por /api/auth/ws-ticket (misma cookie, vía el proxy del frontend) y lo pasa en la
URL del WebSocket. El ticket cifra el token de sesión y caduca en segundos.
"""

from cryptography.fernet import Fernet, InvalidToken

TICKET_TTL_SECONDS = 60


class WsTickets:
    def __init__(self, allowed_origins: list[str], key: bytes | None = None) -> None:
        # Clave por proceso: los tickets duran segundos y no necesitan sobrevivir reinicios.
        self._fernet = Fernet(key or Fernet.generate_key())
        self.allowed_origins = {origin.rstrip("/") for origin in allowed_origins if origin}

    def issue(self, session_token: str) -> str:
        return self._fernet.encrypt(session_token.encode()).decode()

    def redeem(self, ticket: str) -> str | None:
        try:
            return self._fernet.decrypt(ticket.encode(), ttl=TICKET_TTL_SECONDS).decode()
        except (InvalidToken, ValueError):
            return None


def parse_origins(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]
