"""
Standardized error handling for the HyphaGraph API.

This module provides:
- Standardized error response schemas
- Custom exception classes with error codes
- Error code registry for frontend consumption
"""
from typing import Optional
from enum import Enum
from pydantic import BaseModel
from fastapi import HTTPException, status

from app.schemas.common_types import ContextObject


class ErrorCode(str, Enum):
    """
    Standardized error codes for the API.

    These codes help the frontend identify error types and provide
    appropriate user feedback and debugging information.
    """
    # Generic errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Authentication errors
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_EMAIL_NOT_VERIFIED = "AUTH_EMAIL_NOT_VERIFIED"
    AUTH_ACCOUNT_DEACTIVATED = "AUTH_ACCOUNT_DEACTIVATED"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"

    # User management errors
    USER_EMAIL_ALREADY_EXISTS = "USER_EMAIL_ALREADY_EXISTS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_WEAK_PASSWORD = "USER_WEAK_PASSWORD"
    USER_INVALID_EMAIL = "USER_INVALID_EMAIL"

    # Entity/Relation errors
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    ENTITY_SLUG_CONFLICT = "ENTITY_SLUG_CONFLICT"
    RELATION_NOT_FOUND = "RELATION_NOT_FOUND"
    RELATION_TYPE_NOT_FOUND = "RELATION_TYPE_NOT_FOUND"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND"

    # LLM/Extraction errors
    LLM_SERVICE_UNAVAILABLE = "LLM_SERVICE_UNAVAILABLE"
    LLM_API_ERROR = "LLM_API_ERROR"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    EXTRACTION_TEXT_TOO_LONG = "EXTRACTION_TEXT_TOO_LONG"
    EXTRACTION_TEXT_TOO_SHORT = "EXTRACTION_TEXT_TOO_SHORT"

    # Document/File errors
    DOCUMENT_PARSE_ERROR = "DOCUMENT_PARSE_ERROR"
    DOCUMENT_TOO_LARGE = "DOCUMENT_TOO_LARGE"
    DOCUMENT_UNSUPPORTED_FORMAT = "DOCUMENT_UNSUPPORTED_FORMAT"
    DOCUMENT_FETCH_FAILED = "DOCUMENT_FETCH_FAILED"

    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONSTRAINT_VIOLATION = "DATABASE_CONSTRAINT_VIOLATION"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"

    # Business logic errors
    INVALID_FILTER_COMBINATION = "INVALID_FILTER_COMBINATION"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    INVALID_PAGINATION = "INVALID_PAGINATION"
    MERGE_CONFLICT = "MERGE_CONFLICT"
    CIRCULAR_RELATION_DETECTED = "CIRCULAR_RELATION_DETECTED"


class ErrorDetail(BaseModel):
    """
    Detailed error information for debugging.

    Attributes:
        code: Machine-readable error code from ErrorCode enum
        message: User-friendly error message (can be translated by frontend)
        details: Developer-friendly detailed explanation
        field: Optional field name for validation errors
        context: Additional context data (e.g., conflicting IDs, constraints)
    """
    code: ErrorCode
    message: str
    details: Optional[str] = None
    field: Optional[str] = None
    context: Optional[ContextObject] = None


class ErrorResponse(BaseModel):
    """
    Standardized error response schema.

    All API errors return this format for consistency.
    """
    error: ErrorDetail


class AppException(HTTPException):
    """
    Base application exception with standardized error details.

    All custom exceptions should inherit from this class to ensure
    consistent error responses across the API.

    Usage:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.ENTITY_NOT_FOUND,
            message="Entity not found",
            details="Entity with ID '123' does not exist",
            context={"entity_id": "123"}
        )
    """
    def __init__(
        self,
        status_code: int,
        error_code: ErrorCode,
        message: str,
        details: Optional[str] = None,
        field: Optional[str] = None,
        context: Optional[ContextObject] = None,
    ):
        error_detail = ErrorDetail(
            code=error_code,
            message=message,
            details=details,
            field=field,
            context=context,
        )

        # Store as both 'detail' (FastAPI standard) and structured format
        super().__init__(
            status_code=status_code,
            detail=message,
        )
        self.error_detail = error_detail


# =============================================================================
# Convenience Exception Classes
# =============================================================================

class EntityNotFoundException(AppException):
    """Entity not found error."""
    def __init__(self, entity_id: str, details: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.ENTITY_NOT_FOUND,
            message=f"Entity not found",
            details=details or f"Entity with ID '{entity_id}' does not exist",
            context={"entity_id": entity_id},
        )


class RelationNotFoundException(AppException):
    """Relation not found error."""
    def __init__(self, relation_id: str, details: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.RELATION_NOT_FOUND,
            message=f"Relation not found",
            details=details or f"Relation with ID '{relation_id}' does not exist",
            context={"relation_id": relation_id},
        )


class SourceNotFoundException(AppException):
    """Source not found error."""
    def __init__(self, source_id: str, details: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.SOURCE_NOT_FOUND,
            message=f"Source not found",
            details=details or f"Source with ID '{source_id}' does not exist",
            context={"source_id": source_id},
        )


class UnauthorizedException(AppException):
    """Unauthorized access error."""
    def __init__(self, message: str = "Unauthorized", details: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message=message,
            details=details,
        )


class ForbiddenException(AppException):
    """Forbidden access error."""
    def __init__(self, message: str = "Forbidden", details: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.FORBIDDEN,
            message=message,
            details=details,
        )


class LLMServiceUnavailableException(AppException):
    """LLM service is not available."""
    def __init__(self, details: Optional[str] = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.LLM_SERVICE_UNAVAILABLE,
            message="LLM service not available",
            details=details or "Please configure OPENAI_API_KEY to enable LLM features",
        )


class ValidationException(AppException):
    """Validation error with field information."""
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[str] = None,
        context: Optional[ContextObject] = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            field=field,
            details=details,
            context=context,
        )


ErrorDetail.model_rebuild()
