"""Errores base que la capa HTTP traduce a respuestas."""


class DomainError(Exception):
    """Una regla de negocio fue violada."""


class NotFoundError(DomainError):
    """El recurso solicitado no existe."""


class ConflictError(DomainError):
    """La operación choca con el estado actual."""


class InvalidDataError(DomainError):
    """Un dato no cumple las reglas del dominio."""


class AuthenticationError(DomainError):
    """No hay una sesión válida."""


class PermissionDeniedError(DomainError):
    """La sesión no tiene permiso para la operación."""
