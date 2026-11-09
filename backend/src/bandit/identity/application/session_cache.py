"""Caché corta de sesiones válidas: evita ir a la base de datos en cada pedido."""

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from bandit.identity.domain.models import User

DEFAULT_TTL = timedelta(seconds=30)
_MAX_ENTRIES = 5_000


@dataclass(frozen=True, slots=True)
class _Entry:
    user: User
    fresh_until: datetime
    session_expires_at: datetime


class SessionCache:
    """Recuerda por pocos segundos qué token pertenece a qué usuario.

    Cerrar sesión o borrar el usuario la invalida al instante. Con varias instancias del
    backend, otra instancia vería el cambio como máximo `ttl` después.
    """

    def __init__(self, ttl: timedelta = DEFAULT_TTL) -> None:
        self._ttl = ttl
        self._entries: OrderedDict[str, _Entry] = OrderedDict()

    def get(self, token_hash: str, now: datetime) -> User | None:
        entry = self._entries.get(token_hash)
        if entry is None:
            return None
        if now >= entry.fresh_until or now >= entry.session_expires_at:
            del self._entries[token_hash]
            return None
        return entry.user

    def put(self, token_hash: str, user: User, session_expires_at: datetime, now: datetime) -> None:
        self._entries[token_hash] = _Entry(user, now + self._ttl, session_expires_at)
        self._entries.move_to_end(token_hash)
        while len(self._entries) > _MAX_ENTRIES:
            self._entries.popitem(last=False)

    def forget(self, token_hash: str) -> None:
        self._entries.pop(token_hash, None)

    def forget_user(self, user_id: UUID) -> None:
        for token_hash in [k for k, e in self._entries.items() if e.user.id == user_id]:
            del self._entries[token_hash]
