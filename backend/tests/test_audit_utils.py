from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.utils import audit
from app.utils.audit import log_audit_event


@pytest.mark.asyncio
async def test_log_audit_event_logs_context_when_commit_fails():
    audit._consecutive_audit_log_failures = 0
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


@pytest.mark.asyncio
async def test_log_audit_event_emits_critical_after_repeated_failures():
    audit._consecutive_audit_log_failures = 0
    db = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock(side_effect=RuntimeError("db unavailable"))
    db.rollback = AsyncMock()

    with (
        patch("app.utils.audit.logger.exception") as mock_exception,
        patch("app.utils.audit.logger.critical") as mock_critical,
    ):
        for _ in range(audit._AUDIT_LOG_FAILURE_THRESHOLD):
            await log_audit_event(
                db=db,
                event_type="token_refresh",
                event_status="failure",
                user_email="user@example.com",
            )

    assert mock_exception.call_count == audit._AUDIT_LOG_FAILURE_THRESHOLD
    mock_critical.assert_called_once()
    assert mock_critical.call_args.kwargs["extra"]["consecutive_failures"] == audit._AUDIT_LOG_FAILURE_THRESHOLD


@pytest.mark.asyncio
async def test_log_audit_event_resets_failure_counter_after_success():
    audit._consecutive_audit_log_failures = audit._AUDIT_LOG_FAILURE_THRESHOLD - 1
    db = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    await log_audit_event(
        db=db,
        event_type="login",
        event_status="success",
        user_email="user@example.com",
    )

    assert audit._consecutive_audit_log_failures == 0
    db.rollback.assert_not_awaited()
