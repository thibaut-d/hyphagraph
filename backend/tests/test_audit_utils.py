from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.utils.audit import log_audit_event


@pytest.mark.asyncio
async def test_log_audit_event_logs_context_when_commit_fails():
    db = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock(side_effect=RuntimeError("db unavailable"))
    db.rollback = AsyncMock()

    with patch("app.utils.audit.logger.exception") as mock_exception:
        await log_audit_event(
            db=db,
            event_type="login",
            event_status="failure",
            user_email="user@example.com",
        )

    db.rollback.assert_awaited_once()
    mock_exception.assert_called_once()
    assert mock_exception.call_args.kwargs["extra"]["event_type"] == "login"
    assert mock_exception.call_args.kwargs["extra"]["event_status"] == "failure"
