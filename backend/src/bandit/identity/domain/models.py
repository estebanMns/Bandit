"""Entidades de identidad."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    password_hash: str
    role: Role
    establishment_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Session:
    token_hash: str
    user_id: UUID
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at
