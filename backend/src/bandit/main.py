"""Punto de entrada ASGI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from bandit.analysis.api.routes import router as analysis_router
from bandit.bootstrap import Application, build_application
from bandit.cameras.api.routes import router as cameras_router
from bandit.cameras.api.routes import video_router
from bandit.directory.api.routes import router as directory_router
from bandit.directory.domain.models import SyncTrigger
from bandit.establishments.api.routes import router as establishments_router
from bandit.faces.api.routes import router as faces_router
from bandit.identity.api.routes import router as identity_router
from bandit.incidents.api.routes import router as incidents_router
from bandit.notifications.api.routes import router as notifications_router
from bandit.places.api.routes import router as places_router
from bandit.realtime.api.routes import router as realtime_router
from bandit.shared.config import Settings, get_settings
from bandit.shared.http import install_error_handlers


def _build_scheduler(application: Application, settings: Settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(application.incidents.purge_evidence.execute, "interval", hours=6)
    scheduler.add_job(
        application.directory.runner.run,
        "interval",
        args=[SyncTrigger.SCHEDULED],
        hours=settings.directory_scrape_interval_hours,
    )
    return scheduler


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    application = build_application(resolved)
    scheduler = _build_scheduler(application, resolved)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await application.identity.bootstrap_admin.execute(
            resolved.bootstrap_admin_email, resolved.bootstrap_admin_password
        )
        await application.identity.sync_demo_admin.execute(resolved.demo_admin)
        scheduler.start()
        await application.cameras.supervisor.start_all()
        await application.directory.runner.start_if_stale()
        yield
        await application.directory.runner.stop()
        await application.cameras.supervisor.stop_all()
        await application.analysis.supervisor.stop_all()
        if application.faces.supervisor is not None:
            await application.faces.supervisor.stop_all()
        await application.background.wait_all()
        scheduler.shutdown(wait=False)
        await application.engine.dispose()

    app = FastAPI(title="Bandit", lifespan=lifespan)
    app.state.identity = application.identity
    app.state.establishments = application.establishments
    app.state.cameras = application.cameras
    app.state.analysis = application.analysis
    app.state.incidents = application.incidents
    app.state.notifications = application.notifications
    app.state.directory = application.directory
    app.state.faces = application.faces
    app.state.places = application.places
    app.state.event_hub = application.event_hub
    install_error_handlers(app)
    for router in (
        identity_router,
        establishments_router,
        cameras_router,
        video_router,
        analysis_router,
        incidents_router,
        notifications_router,
        directory_router,
        faces_router,
        places_router,
        realtime_router,
    ):
        app.include_router(router)

    @app.get("/api/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
