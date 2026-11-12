"""Dependencias HTTP y WebSocket de autenticación."""

import hmac
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, Request, WebSocket

from bandit.identity.api.ws_tickets import WsTickets
from bandit.identity.domain.models import Role, User
from bandit.identity.module import IdentityModule
from bandit.shared.errors import AuthenticationError, PermissionDeniedError

SESSION_COOKIE = "bandit_session"
CSRF_COOKIE = "bandit_csrf"
CSRF_HEADER = "x-csrf-token"


def _module(request: Request) -> IdentityModule:
    module: IdentityModule = request.app.state.identity
    return module


async def current_user(
    request: Request, module: Annotated[IdentityModule, Depends(_module)]
) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise AuthenticationError("Inicia sesión para continuar")
    return await module.authenticate.execute(token)


CurrentUser = Annotated[User, Depends(current_user)]


def require_csrf(request: Request) -> None:
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    if not cookie or not hmac.compare_digest(cookie, header):
        raise PermissionDeniedError("Falta el token CSRF")


def require_admin(user: CurrentUser) -> User:
    if user.role is not Role.ADMIN:
        raise PermissionDeniedError("Esta acción requiere un administrador")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_manager(user: CurrentUser) -> User:
    """Puede administrar un local. Cada ruta debe comprobar además cuál."""
    if user.role not in (Role.ADMIN, Role.OWNER):
        raise PermissionDeniedError("Esta acción requiere al dueño del local")
    return user


ManagerUser = Annotated[User, Depends(require_manager)]


async def authenticate_websocket(websocket: WebSocket) -> User:
    """Valida sesión y origen: un WebSocket no tiene la protección CORS del navegador."""
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host")
    tickets: WsTickets | None = getattr(websocket.app.state, "ws_tickets", None)
    allowed = tickets.allowed_origins if tickets else set()
    if origin and urlsplit(origin).netloc != host and origin.rstrip("/") not in allowed:
        raise PermissionDeniedError("Origen no permitido")
    token = websocket.cookies.get(SESSION_COOKIE)
    ticket = websocket.query_params.get("ticket")
    if ticket and tickets is not None:
        token = tickets.redeem(ticket)
    if not token:
        raise AuthenticationError("Inicia sesión para continuar")
    module: IdentityModule = websocket.app.state.identity
    return await module.authenticate.execute(token)
