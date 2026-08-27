"""Domain-level API exceptions and their FastAPI exception handlers,
mapped to one consistent `{"error": {"code", "message", "details"}}`
envelope (M6 Sec. 20-21). Service/business code raises these; route
handlers never construct an error response themselves, and internal
exception details/stack traces never reach the client (M6 Sec. 13/32).
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.api.errors")


class APIError(Exception):
    """Base class for every domain-level error this API raises
    deliberately. Route handlers should let these propagate — never catch
    and re-wrap them — so the registered handler below is what turns them
    into a response."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"

    def __init__(self, message: str, details: list[dict] | None = None):
        self.message = message
        self.details = details or []
        super().__init__(message)


class NotFoundError(APIError):
    """Unknown ATC class, missing forecast/model, etc."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class BadRequestError(APIError):
    """Invalid date range, unsupported grain, invalid scenario name, etc.
    — malformed input that Pydantic's own field validation doesn't catch
    because it depends on cross-field or data-driven rules."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"


class OptimizationInfeasibleError(APIError):
    """The OR-Tools solver returned an infeasible/unbounded status for the
    requested scenario parameters (app.optimization.allocation_optimizer)."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "optimization_infeasible"


class ServiceUnavailableError(APIError):
    """A required upstream dependency (database, raw data files, model
    registry) is not reachable/populated."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "service_unavailable"


def _error_response(status_code: int, code: str, message: str, details: list[dict] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or []}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("Unhandled domain error on %s %s: %s", request.method, request.url.path, exc.message)
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]} for err in exc.errors()
        ]
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "validation_error", "Request validation failed.", details
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Never leak the exception message or a stack trace to the client
        # (M6 Sec. 13/32) — log the real detail server-side only.
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "internal_error", "An unexpected error occurred."
        )
