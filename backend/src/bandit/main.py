"""Punto de entrada ASGI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bandit.bootstrap import build_application
from bandit.identity.api.routes import router as identity_router
from bandit.shared.config import Settings, get_settings
from bandit.shared.http import install_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    application = build_application(resolved)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await application.identity.bootstrap_admin.execute(
            resolved.bootstrap_admin_email, resolved.bootstrap_admin_password
        )
        yield
        await application.engine.dispose()

    app = FastAPI(title="Bandit", lifespan=lifespan)
    app.state.identity = application.identity
    install_error_handlers(app)
    app.include_router(identity_router)

    @app.get("/api/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
