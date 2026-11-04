"""Rutas de locales."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from bandit.establishments.domain.models import Establishment
from bandit.establishments.module import EstablishmentsModule
from bandit.identity.public import AdminUser, CurrentUser, User, require_csrf
from bandit.shared.errors import PermissionDeniedError

router = APIRouter(prefix="/api/establishments", tags=["establishments"])


def _module(request: Request) -> EstablishmentsModule:
    module: EstablishmentsModule = request.app.state.establishments
    return module


Module = Annotated[EstablishmentsModule, Depends(_module)]


class CreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: str = Field(min_length=1, max_length=300)


class WhatsAppRequest(BaseModel):
    number: str | None = Field(default=None, max_length=30)


class EstablishmentResponse(BaseModel):
    id: UUID
    name: str
    address: str
    cai_whatsapp: str | None

    @classmethod
    def of(cls, establishment: Establishment) -> "EstablishmentResponse":
        number = establishment.cai_whatsapp
        return cls(
            id=establishment.id,
            name=establishment.name,
            address=establishment.address,
            cai_whatsapp=number.value if number else None,
        )


def _ensure_access(user: User, establishment_id: UUID) -> None:
    if not user.can_access(establishment_id):
        raise PermissionDeniedError("No tienes acceso a este local")


@router.get("")
async def list_establishments(user: CurrentUser, module: Module) -> list[EstablishmentResponse]:
    establishments = await module.list_all.execute()
    return [EstablishmentResponse.of(e) for e in establishments if user.can_access(e.id)]


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
async def create_establishment(
    body: CreateRequest, _: AdminUser, module: Module
) -> EstablishmentResponse:
    return EstablishmentResponse.of(await module.create.execute(body.name, body.address))


@router.get("/{establishment_id}")
async def get_establishment(
    establishment_id: UUID, user: CurrentUser, module: Module
) -> EstablishmentResponse:
    _ensure_access(user, establishment_id)
    return EstablishmentResponse.of(await module.get.execute(establishment_id))


@router.put("/{establishment_id}/cai-whatsapp", dependencies=[Depends(require_csrf)])
async def set_cai_whatsapp(
    establishment_id: UUID, body: WhatsAppRequest, user: CurrentUser, module: Module
) -> EstablishmentResponse:
    _ensure_access(user, establishment_id)
    return EstablishmentResponse.of(
        await module.set_cai_whatsapp.execute(establishment_id, body.number)
    )
