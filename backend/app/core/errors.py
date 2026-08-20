from typing import Any


class AeroError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        status: int = 400,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        self.status = status
        super().__init__(message)


class NotFoundError(AeroError):
    def __init__(self, message: str = "not found", details: dict[str, Any] | None = None) -> None:
        super().__init__("NOT_FOUND", message, details, 404)


class UnauthorizedError(AeroError):
    def __init__(
        self,
        message: str = "unauthorized",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("UNAUTHORIZED", message, details, 401)


class ForbiddenError(AeroError):
    def __init__(
        self,
        message: str = "forbidden",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("FORBIDDEN", message, details, 403)


class ConflictError(AeroError):
    def __init__(
        self,
        message: str = "conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("CONFLICT", message, details, 409)


class VersionConflictError(AeroError):
    def __init__(self, details: dict[str, Any]) -> None:
        super().__init__("VERSION_CONFLICT", "version conflict", details, 409)


class BadRequestError(AeroError):
    def __init__(
        self,
        message: str = "bad request",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("BAD_REQUEST", message, details, 400)


class InvalidAnchorError(AeroError):
    def __init__(
        self,
        message: str = "invalid inline anchor",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__("INVALID_ANCHOR", message, details, 400)
