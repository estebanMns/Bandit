"""Rutas del directorio. Solo informan: nada aquí se cruza con el video."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from bandit.directory.domain.models import SyncReport, WantedRecord
from bandit.directory.module import DirectoryModule
from bandit.identity.public import AdminUser, require_csrf
from bandit.shared.errors import NotFoundError

router = APIRouter(prefix="/api/directory", tags=["directory"])

_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def _module(request: Request) -> DirectoryModule:
    module: DirectoryModule = request.app.state.directory
    return module


Module = Annotated[DirectoryModule, Depends(_module)]


class WantedResponse(BaseModel):
    slug: str
    name: str
    alias: str | None
    crime: str | None
    reward: str | None
    region: str | None
    hotline_email: str | None
    hotline_phones: list[str]
    photo_url: str | None
    flyer_url: str | None
    source_url: str
    last_seen_at: datetime | None

    @classmethod
    def of(cls, record: WantedRecord) -> "WantedResponse":
        return cls(
            slug=record.slug,
            name=record.name,
            alias=record.alias,
            crime=record.crime,
            reward=record.reward,
            region=record.region,
            hotline_email=record.hotline_email,
            hotline_phones=record.hotline_phones,
            photo_url=f"/api/directory/media/{record.photo_file}" if record.photo_file else None,
            flyer_url=f"/api/directory/media/{record.flyer_file}" if record.flyer_file else None,
            source_url=record.source_url,
            last_seen_at=record.last_seen_at,
        )


class SyncResponse(BaseModel):
    published: int
    rejected: int
    retired: int
    completed: bool

    @classmethod
    def of(cls, report: SyncReport) -> "SyncResponse":
        return cls(
            published=report.published,
            rejected=report.rejected,
            retired=report.retired,
            completed=report.completed,
        )


@router.get("")
async def list_wanted(module: Module) -> list[WantedResponse]:
    return [WantedResponse.of(record) for record in await module.list_active.execute()]


@router.post("/sync", dependencies=[Depends(require_csrf)])
async def sync_directory(_: AdminUser, module: Module) -> SyncResponse:
    return SyncResponse.of(await module.sync.execute())


@router.get("/media/{name}")
async def get_media(name: str, module: Module) -> FileResponse:
    path = module.media.path_of(name)
    media_type = _MEDIA_TYPES.get(name[name.rfind(".") :].lower())
    if path is None or media_type is None:
        raise NotFoundError("El archivo no existe")
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Cross-Origin-Resource-Policy": "same-origin",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.get("/{slug}")
async def get_wanted(slug: str, module: Module) -> WantedResponse:
    return WantedResponse.of(await module.get.execute(slug))
