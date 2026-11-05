"""Rutas de notificaciones."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import AnyHttpUrl, BaseModel, Field

from bandit.identity.public import CurrentUser, ManagerUser, User, require_csrf
from bandit.notifications.domain.models import PushTarget
from bandit.notifications.module import NotificationsModule
from bandit.shared.errors import DomainError, PermissionDeniedError

router = APIRouter(prefix="/api/establishments/{establishment_id}", tags=["notifications"])


def _module(request: Request) -> NotificationsModule:
    module: NotificationsModule = request.app.state.notifications
    return module


Module = Annotated[NotificationsModule, Depends(_module)]


class PushKeys(BaseModel):
    p256dh: str = Field(max_length=200)
    auth: str = Field(max_length=100)


class PushSubscriptionRequest(BaseModel):
    endpoint: AnyHttpUrl
    keys: PushKeys


def _ensure_access(user: User, establishment_id: UUID) -> None:
    if not user.can_access(establishment_id):
        raise PermissionDeniedError("No tienes acceso a este local")


@router.post(
    "/whatsapp-test",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def send_whatsapp_test(establishment_id: UUID, user: ManagerUser, module: Module) -> None:
    _ensure_access(user, establishment_id)
    try:
        await module.send_test_message.execute(establishment_id)
    except DomainError:
        raise
    except Exception as error:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "WhatsApp rechazó el mensaje. Revisa el número y la configuración.",
        ) from error


@router.post(
    "/push-subscriptions",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_csrf)],
)
async def subscribe_push(
    establishment_id: UUID, body: PushSubscriptionRequest, user: CurrentUser, module: Module
) -> None:
    _ensure_access(user, establishment_id)
    await module.register_push_target.execute(
        establishment_id, PushTarget(str(body.endpoint), body.keys.p256dh, body.keys.auth)
    )
