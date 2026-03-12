import json
from types import SimpleNamespace

import pytest
from fastapi import status
from starlette.requests import Request

from app.middleware.error_handler import rate_limit_exception_handler
from app.utils.errors import ErrorCode


@pytest.mark.asyncio
async def test_rate_limit_exception_handler_returns_standardized_error_shape():
    request = Request({"type": "http", "method": "GET", "path": "/api/test", "headers": []})
    exception = SimpleNamespace(detail="5 per minute")

    response = await rate_limit_exception_handler(request, exception)  # type: ignore[arg-type]

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    payload = json.loads(response.body)
    assert payload == {
        "error": {
            "code": ErrorCode.RATE_LIMIT_EXCEEDED,
            "message": "Too many requests. Please try again later.",
            "details": "5 per minute",
        }
    }
