"""
API error handling decorators and utilities.

Provides consistent error handling across API endpoints.
"""
import logging
from functools import wraps
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from fastapi import status
from pydantic import ValidationError

from app.llm.base import LLMError
from app.utils.errors import AppException, ErrorCode

logger = logging.getLogger(__name__)
Params = ParamSpec("Params")
ReturnT = TypeVar("ReturnT")


def handle_extraction_errors(
    func: Callable[Params, Awaitable[ReturnT]],
) -> Callable[Params, Awaitable[ReturnT]]:
    """
    Decorator to handle extraction errors consistently.

    Catches all exceptions from extraction endpoints and converts them to
    appropriate AppException responses with proper status codes and error codes.

    Preserves AppExceptions as-is (re-raises them without modification).
    Converts all other exceptions to EXTRACTION_FAILED AppExceptions.

    Usage:
        @handle_extraction_errors
        async def extract_entities(request, user, service):
            entities = await service.extract_entities(...)
            return EntityExtractionResponse(...)

    Args:
        func: The endpoint function to wrap

    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    async def wrapper(*args: Params.args, **kwargs: Params.kwargs) -> ReturnT:
        try:
            return await func(*args, **kwargs)
        except AppException:
            # Re-raise AppExceptions to preserve their structured error details
            raise
        except LLMError as exc:
            logger.exception("LLM extraction operation failed in %s", func.__name__)
            raise AppException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code=ErrorCode.LLM_SERVICE_UNAVAILABLE,
                message="LLM service not available",
                details=str(exc),
            ) from exc
        except ValidationError as exc:
            logger.exception("Extraction validation failed in %s", func.__name__)

            errors = exc.errors()
            if errors:
                first_error = errors[0]
                field = ".".join(str(loc) for loc in first_error.get("loc", []))
                message = first_error.get("msg", "Validation error")
                display_message = f"Invalid {field}: {message}" if field else message
                details = f"Field '{field}' failed validation: {message}" if field else message
            else:
                field = None
                display_message = "Validation error"
                details = "The extraction response failed validation"

            raise AppException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ErrorCode.VALIDATION_ERROR,
                message=display_message,
                details=details,
                field=field,
                context={"validation_errors": errors} if errors else None,
            ) from exc
        except ValueError as exc:
            logger.warning(
                "Validation error in extraction endpoint %s: %s",
                func.__name__,
                exc,
            )
            raise AppException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code=ErrorCode.VALIDATION_ERROR,
                message="Invalid extraction input",
                details=str(exc),
            )
        except Exception as exc:
            # Log with full traceback for server-side diagnostics
            logger.exception("Extraction operation failed in %s", func.__name__)

            # Wrap in AppException — preserve the original message as `details` so
            # developer tooling (dev Snackbar, logs) can show the root cause while
            # keeping the user-facing message generic.
            raise AppException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=ErrorCode.EXTRACTION_FAILED,
                message=f"{func.__name__.replace('_', ' ').title()} failed",
                details=str(exc) or type(exc).__name__,
            )

    return wrapper
