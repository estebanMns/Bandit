"""Traducción de errores de dominio a respuestas HTTP."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from bandit.shared.errors import (
    AuthenticationError,
    ConflictError,
    DomainError,
    InvalidDataError,
    NotFoundError,
    PermissionDeniedError,
)

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    InvalidDataError: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def install_error_handlers(app: FastAPI) -> None:
    async def handle(_: Request, error: Exception) -> JSONResponse:
        code = _STATUS_BY_ERROR.get(type(error), status.HTTP_400_BAD_REQUEST)
        return JSONResponse({"detail": str(error)}, status_code=code)

    app.add_exception_handler(DomainError, handle)
