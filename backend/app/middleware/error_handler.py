"""
Global error handling middleware for the HyphaGraph API.

This middleware catches all unhandled exceptions and converts them
to standardized error responses.
"""
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from slowapi.errors import RateLimitExceeded

from app.utils.errors import (
    ErrorCode,
    ErrorDetail,
    AppException,
)

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle AppException instances.

    These are our custom exceptions with structured error details.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": exc.error_detail.model_dump(exclude_none=True),
        },
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError | ValidationError,
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Converts FastAPI's validation errors into our standardized format.
    """
    # Extract field-specific errors
    errors = exc.errors() if hasattr(exc, "errors") else []

    # Build a user-friendly message
    if errors:
        first_error = errors[0]
        field = ".".join(str(loc) for loc in first_error.get("loc", []))
        message = first_error.get("msg", "Validation error")

        error_detail = ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Invalid {field}: {message}",
            details=f"Field '{field}' failed validation: {message}",
            field=field,
            context={"validation_errors": errors},
        )
    else:
        error_detail = ErrorDetail(
            code=ErrorCode.VALIDATION_ERROR,
            message="Validation error",
            details="The request data failed validation",
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": error_detail.message,
            "error": error_detail.model_dump(exclude_none=True),
        },
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """
    Handle database integrity constraint violations.

    Examples: unique constraint, foreign key constraint, not null constraint.
    """
    error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)

    # Try to extract meaningful info from PostgreSQL error messages
    if "unique constraint" in error_msg.lower():
        # Extract constraint name if possible
        constraint = error_msg.split("DETAIL:")[0] if "DETAIL:" in error_msg else error_msg

        error_detail = ErrorDetail(
            code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
            message="Duplicate entry detected",
            details=f"A record with this value already exists: {constraint}",
            context={"constraint_type": "unique", "error": error_msg},
        )
    elif "foreign key constraint" in error_msg.lower():
        error_detail = ErrorDetail(
            code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
            message="Referenced record not found",
            details="The operation references a non-existent record",
            context={"constraint_type": "foreign_key", "error": error_msg},
        )
    elif "not null constraint" in error_msg.lower():
        error_detail = ErrorDetail(
            code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
            message="Required field missing",
            details="A required field was not provided",
            context={"constraint_type": "not_null", "error": error_msg},
        )
    else:
        error_detail = ErrorDetail(
            code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
            message="Database constraint violation",
            details=error_msg,
            context={"error": error_msg},
        )

    logger.error(f"Database integrity error: {error_msg}", exc_info=exc)

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": error_detail.model_dump(exclude_none=True)},
    )


async def operational_error_handler(
    request: Request,
    exc: OperationalError,
) -> JSONResponse:
    """
    Handle database operational errors.

    Examples: connection errors, timeout errors.
    """
    error_msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)

    error_detail = ErrorDetail(
        code=ErrorCode.DATABASE_CONNECTION_ERROR,
        message="Database connection error",
        details="Unable to connect to the database. Please try again later.",
        context={"error": error_msg},
    )

    logger.error(f"Database operational error: {error_msg}", exc_info=exc)

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"error": error_detail.model_dump(exclude_none=True)},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    Logs the full error for debugging but returns a generic message to users.
    """
    # Log the full error for debugging
    logger.exception(f"Unhandled exception: {exc}", exc_info=exc)

    # Return a generic error to avoid leaking sensitive information
    error_detail = ErrorDetail(
        code=ErrorCode.INTERNAL_SERVER_ERROR,
        message="Internal server error",
        details="An unexpected error occurred. Please try again later.",
        context={"error_type": type(exc).__name__} if logger.isEnabledFor(logging.DEBUG) else None,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": error_detail.model_dump(exclude_none=True)},
    )


async def rate_limit_exception_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """
    Return rate limit errors using the same structured error envelope as the rest of the API.
    """
    detail = getattr(exc, "detail", None) or "Rate limit exceeded"
    error_detail = ErrorDetail(
        code=ErrorCode.RATE_LIMIT_EXCEEDED,
        message="Too many requests. Please try again later.",
        details=str(detail),
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"error": error_detail.model_dump(exclude_none=True)},
    )


def register_error_handlers(app) -> None:
    """
    Register all error handlers with the FastAPI application.

    This should be called during application startup.
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(OperationalError, operational_error_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Error handlers registered successfully")
