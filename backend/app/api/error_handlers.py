"""
API error handling decorators and utilities.

Provides consistent error handling across API endpoints.
"""
import logging
from functools import wraps
from typing import Callable, Any

from fastapi import status

from app.utils.errors import AppException, ErrorCode

logger = logging.getLogger(__name__)


def handle_extraction_errors(func: Callable) -> Callable:
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
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except AppException:
            # Re-raise AppExceptions to preserve error details
            raise
        except Exception as e:
            # Log the error
            logger.error(f"Extraction operation failed in {func.__name__}: {e}")

            # Convert to standard AppException
            raise AppException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=ErrorCode.EXTRACTION_FAILED,
                message=f"{func.__name__.replace('_', ' ').title()} failed",
                details=str(e)
            )

    return wrapper
