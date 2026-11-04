"""Punto de entrada ASGI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from bandit.bootstrap import build_application
from bandit.cameras.api.routes import router as cameras_router
from bandit.cameras.api.routes import video_router
from bandit.establishments.api.routes import router as establishments_router
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
        await application.cameras.supervisor.start_all()
        yield
        await application.cameras.supervisor.stop_all()
        await application.engine.dispose()

    app = FastAPI(title="Bandit", lifespan=lifespan)
    app.state.identity = application.identity
    app.state.establishments = application.establishments
    app.state.cameras = application.cameras
    install_error_handlers(app)
    app.include_router(identity_router)
    app.include_router(establishments_router)
    app.include_router(cameras_router)
    app.include_router(video_router)

    @app.get("/api/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
