"""Composición del módulo de locales."""

from bandit.establishments.application.use_cases import (
    CreateEstablishment,
    GetEstablishment,
    ListEstablishments,
    SetCaiWhatsApp,
)
from bandit.establishments.infrastructure.repositories import SqlEstablishmentRepository
from bandit.shared.db import SessionFactory


class EstablishmentsModule:
    def __init__(self, sessions: SessionFactory) -> None:
        repository = SqlEstablishmentRepository(sessions)
        self.create = CreateEstablishment(repository)
        self.get = GetEstablishment(repository)
        self.list_all = ListEstablishments(repository)
        self.set_cai_whatsapp = SetCaiWhatsApp(repository, self.get)
