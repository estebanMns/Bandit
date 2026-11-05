"""Rutas de sesión."""

import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from bandit.identity.api.deps import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    AdminUser,
    CurrentUser,
    _module,
    require_csrf,
)
from bandit.identity.domain.models import Role, User
from bandit.identity.module import IdentityModule

router = APIRouter(prefix="/api/auth", tags=["auth"])
Module = Annotated[IdentityModule, Depends(_module)]


class LoginRequest(BaseModel):
    # Sin EmailStr: un correo interno como admin@bandit.local también debe poder ingresar.
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(BaseModel):
    """Sin campo de rol: el registro siempre crea un dueño."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    local_name: str = Field(min_length=1, max_length=200)
    local_address: str = Field(min_length=1, max_length=300)


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    role: Role = Role.OPERATOR
    establishment_id: UUID | None = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: Role
    establishment_id: UUID | None

    @classmethod
    def of(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            establishment_id=user.establishment_id,
        )


def _set_session_cookies(response: Response, module: IdentityModule, token: str) -> None:
    max_age = int(module.session_ttl.total_seconds())
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        secure=module.cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_urlsafe(32),
        max_age=max_age,
        httponly=False,
        secure=module.cookie_secure,
        samesite="lax",
        path="/",
    )


def _client_key(request: Request) -> str:
    # Caddy reemplaza esta cabecera con la IP real: el cliente no puede falsificarla.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "desconocido"


@router.post("/login")
async def login(body: LoginRequest, response: Response, module: Module) -> UserResponse:
    issued = await module.login.execute(body.email, body.password)
    _set_session_cookies(response, module, issued.token)
    return UserResponse.of(issued.user)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest, request: Request, response: Response, module: Module
) -> UserResponse:
    await module.sign_up.execute(
        body.email, body.password, body.local_name, body.local_address, _client_key(request)
    )
    issued = await module.login.execute(body.email, body.password)
    _set_session_cookies(response, module, issued.token)
    return UserResponse.of(issued.user)


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_csrf)]
)
async def logout(request: Request, response: Response, module: Module) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await module.logout.execute(token)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


@router.get("/me")
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.of(user)


@router.post("/users", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_csrf)])
async def create_user(body: CreateUserRequest, _: AdminUser, module: Module) -> UserResponse:
    user = await module.register_user.execute(
        body.email, body.password, body.role, body.establishment_id
    )
    return UserResponse.of(user)
