"""Composición del módulo de identidad."""

from datetime import timedelta

from bandit.identity.application.throttle import AttemptThrottle
from bandit.identity.application.use_cases import (
    AuthenticateSession,
    BootstrapAdmin,
    Login,
    Logout,
    RegisterUser,
    SignUp,
)
from bandit.identity.domain.ports import EstablishmentCreator
from bandit.identity.infrastructure.argon2_hasher import Argon2PasswordHasher
from bandit.identity.infrastructure.repositories import SqlSessionRepository, SqlUserRepository
from bandit.shared.clock import Clock
from bandit.shared.db import SessionFactory


class IdentityModule:
    def __init__(
        self,
        sessions: SessionFactory,
        clock: Clock,
        session_ttl: timedelta,
        cookie_secure: bool,
        establishments: EstablishmentCreator,
    ) -> None:
        users = SqlUserRepository(sessions)
        session_repository = SqlSessionRepository(sessions)
        hasher = Argon2PasswordHasher()

        self.cookie_secure = cookie_secure
        self.session_ttl = session_ttl
        self.register_user = RegisterUser(users, hasher)
        self.bootstrap_admin = BootstrapAdmin(users, self.register_user)
        self.login = Login(users, session_repository, hasher, clock, session_ttl, AttemptThrottle())
        self.sign_up = SignUp(
            self.register_user,
            establishments,
            AttemptThrottle(max_attempts=5, window=timedelta(hours=1)),
            clock,
        )
        self.logout = Logout(session_repository)
        self.authenticate = AuthenticateSession(users, session_repository, clock)
