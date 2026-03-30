import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.exceptions import RequestValidationError
from pydantic_core import InitErrorDetails
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.requests import Request

from app.middleware.error_handler import (
    app_exception_handler,
    generic_exception_handler,
    integrity_error_handler,
    operational_error_handler,
    rate_limit_exception_handler,
    validation_exception_handler,
)
from app.utils.errors import AppException, ErrorCode


def _make_request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/api/test", "headers": []})


# ---------------------------------------------------------------------------
# Canonical envelope: every handler must return {"error": {...}} with no
# top-level "detail" key.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_app_exception_handler_canonical_envelope():
    request = _make_request()
    exc = AppException(
        status_code=status.HTTP_404_NOT_FOUND,
        error_code=ErrorCode.ENTITY_NOT_FOUND,
        message="Entity not found",
        details="Entity with ID 'abc' does not exist",
        context={"entity_id": "abc"},
    )

    response = await app_exception_handler(request, exc)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    payload = json.loads(response.body)
    assert "detail" not in payload, "Top-level 'detail' key must not appear in error responses"
    assert payload == {
        "error": {
            "code": ErrorCode.ENTITY_NOT_FOUND,
            "message": "Entity not found",
            "details": "Entity with ID 'abc' does not exist",
            "context": {"entity_id": "abc"},
        }
    }


@pytest.mark.asyncio
async def test_validation_exception_handler_canonical_envelope():
    request = _make_request()
    # Build a minimal RequestValidationError
    raw_errors = [{"type": "missing", "loc": ("body", "slug"), "msg": "Field required", "input": {}}]
    exc = RequestValidationError(errors=raw_errors)

    response = await validation_exception_handler(request, exc)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    payload = json.loads(response.body)
    assert "detail" not in payload, "Top-level 'detail' key must not appear in validation responses"
    assert "error" in payload
    assert payload["error"]["code"] == ErrorCode.VALIDATION_ERROR
    assert payload["error"]["field"] == "body.slug"


@pytest.mark.asyncio
async def test_integrity_error_handler_canonical_envelope():
    request = _make_request()
    orig = MagicMock()
    orig.__str__ = lambda self: "UNIQUE constraint failed: entity_revisions.slug"
    exc = IntegrityError("stmt", "params", orig)

    response = await integrity_error_handler(request, exc)

    assert response.status_code == status.HTTP_409_CONFLICT
    payload = json.loads(response.body)
    assert "detail" not in payload
    assert payload["error"]["code"] == ErrorCode.DATABASE_CONSTRAINT_VIOLATION


@pytest.mark.asyncio
async def test_operational_error_handler_canonical_envelope():
    request = _make_request()
    orig = MagicMock()
    orig.__str__ = lambda self: "could not connect to server"
    exc = OperationalError("stmt", "params", orig)

    response = await operational_error_handler(request, exc)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    payload = json.loads(response.body)
    assert "detail" not in payload
    assert payload["error"]["code"] == ErrorCode.DATABASE_CONNECTION_ERROR


@pytest.mark.asyncio
async def test_generic_exception_handler_canonical_envelope():
    request = _make_request()
    exc = ValueError("something unexpected")

    response = await generic_exception_handler(request, exc)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    payload = json.loads(response.body)
    assert "detail" not in payload
    assert payload["error"]["code"] == ErrorCode.INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
async def test_rate_limit_exception_handler_returns_standardized_error_shape():
    request = _make_request()
    exception = SimpleNamespace(detail="5 per minute")

    response = await rate_limit_exception_handler(request, exception)  # type: ignore[arg-type]

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    payload = json.loads(response.body)
    assert "detail" not in payload
    assert payload == {
        "error": {
            "code": ErrorCode.RATE_LIMIT_EXCEEDED,
            "message": "Too many requests. Please try again later.",
            "details": "5 per minute",
        }
    }


# ---------------------------------------------------------------------------
# ErrorCode enum completeness snapshot.
# All values that appear in the backend enum must be a known set so that
# frontend enum drift is detected in CI.
# ---------------------------------------------------------------------------

EXPECTED_BACKEND_ERROR_CODES = {
    # Generic
    "INTERNAL_SERVER_ERROR",
    "VALIDATION_ERROR",
    "NOT_FOUND",
    "UNAUTHORIZED",
    "FORBIDDEN",
    "RATE_LIMIT_EXCEEDED",
    # Auth
    "AUTH_INVALID_CREDENTIALS",
    "AUTH_TOKEN_EXPIRED",
    "AUTH_TOKEN_INVALID",
    "AUTH_EMAIL_NOT_VERIFIED",
    "AUTH_ACCOUNT_DEACTIVATED",
    "AUTH_INSUFFICIENT_PERMISSIONS",
    # User mgmt
    "USER_EMAIL_ALREADY_EXISTS",
    "USER_NOT_FOUND",
    "USER_WEAK_PASSWORD",
    "USER_INVALID_EMAIL",
    # Entity / Relation
    "ENTITY_NOT_FOUND",
    "ENTITY_SLUG_CONFLICT",
    "ENTITY_HAS_RELATIONS",
    "RELATION_NOT_FOUND",
    "RELATION_TYPE_NOT_FOUND",
    "SOURCE_NOT_FOUND",
    # LLM / Extraction
    "LLM_SERVICE_UNAVAILABLE",
    "LLM_API_ERROR",
    "LLM_RATE_LIMIT",
    "EXTRACTION_FAILED",
    "EXTRACTION_TEXT_TOO_LONG",
    "EXTRACTION_TEXT_TOO_SHORT",
    # Document / File
    "DOCUMENT_PARSE_ERROR",
    "DOCUMENT_TOO_LARGE",
    "DOCUMENT_UNSUPPORTED_FORMAT",
    "DOCUMENT_FETCH_FAILED",
    # Database
    "DATABASE_ERROR",
    "DATABASE_CONSTRAINT_VIOLATION",
    "DATABASE_CONNECTION_ERROR",
    # Business logic
    "INVALID_FILTER_COMBINATION",
    "INVALID_DATE_RANGE",
    "INVALID_PAGINATION",
    "MERGE_CONFLICT",
    "CIRCULAR_RELATION_DETECTED",
}


def test_error_code_enum_matches_known_set():
    """
    Snapshot test: fail if backend ErrorCode gains or loses values without a
    corresponding frontend enum update.  When this test fails, update both
    EXPECTED_BACKEND_ERROR_CODES above and frontend/src/utils/errorHandler.ts.
    """
    actual = {code.value for code in ErrorCode}
    added = actual - EXPECTED_BACKEND_ERROR_CODES
    removed = EXPECTED_BACKEND_ERROR_CODES - actual
    assert not added, f"New ErrorCode values not yet in frontend enum: {added}"
    assert not removed, f"ErrorCode values removed but still in snapshot: {removed}"
