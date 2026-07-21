"""Domain error types and exception handlers."""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Request could not be processed."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Resource not found."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    default_message = "You do not have permission to perform this action."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    default_message = "The request conflicts with existing state."


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
