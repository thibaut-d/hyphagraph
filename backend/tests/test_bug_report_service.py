"""
Tests for BugReportService — CAPTCHA generation/verification and report creation.
"""
import time
from unittest.mock import patch

import pytest

from app.models.bug_report import BugReport
from app.services.bug_report_service import BugReportService, _CAPTCHA_TTL


# ---------------------------------------------------------------------------
# CAPTCHA tests (pure logic, no DB)
# ---------------------------------------------------------------------------

class TestCaptcha:
    def test_generate_returns_token_and_question(self):
        challenge = BugReportService.generate_captcha()
        assert challenge.token
        assert "?" in challenge.question

    def test_valid_answer_verifies(self):
        challenge = BugReportService.generate_captcha()
        # Extract expected answer from token internals via verify round-trip
        import base64
        raw = base64.urlsafe_b64decode(challenge.token.encode()).decode()
        expected_answer = raw.split(":")[0]
        assert BugReportService.verify_captcha(challenge.token, expected_answer)

    def test_wrong_answer_rejected(self):
        challenge = BugReportService.generate_captcha()
        assert not BugReportService.verify_captcha(challenge.token, "9999")

    def test_expired_token_rejected(self):
        # Build a token with expiry in the past
        past_expiry = int(time.time()) - 1
        token = BugReportService._sign_captcha("5", past_expiry, "testnonce")
        assert not BugReportService.verify_captcha(token, "5")

    def test_tampered_token_rejected(self):
        challenge = BugReportService.generate_captcha()
        tampered = challenge.token[:-4] + "XXXX"
        import base64
        raw = base64.urlsafe_b64decode(challenge.token.encode()).decode()
        answer = raw.split(":")[0]
        assert not BugReportService.verify_captcha(tampered, answer)

    def test_malformed_token_rejected(self):
        assert not BugReportService.verify_captcha("not-base64!!!", "5")

    def test_malformed_token_logs_warning(self):
        with patch("app.services.bug_report_service.logger.warning") as warning_mock:
            assert not BugReportService.verify_captcha("not-base64!!!", "5")

        warning_mock.assert_called_once_with(
            "CAPTCHA decode failed — malformed token (possible tampering attempt)"
        )

    def test_whitespace_in_answer_stripped(self):
        challenge = BugReportService.generate_captcha()
        import base64
        raw = base64.urlsafe_b64decode(challenge.token.encode()).decode()
        expected_answer = raw.split(":")[0]
        assert BugReportService.verify_captcha(challenge.token, f"  {expected_answer}  ")

    def test_token_with_valid_base64_but_missing_colons_rejected(self):
        """A token that decodes cleanly but lacks the 3-part colon structure is rejected."""
        import base64
        # Valid base64, but no colons — split(":") returns a 1-element list
        bad = base64.urlsafe_b64encode(b"nodividers").decode()
        assert not BugReportService.verify_captcha(bad, "5")

    def test_concurrent_captcha_tokens_are_independent(self):
        """Multiple tokens generated in sequence have distinct values and each verifies independently."""
        import base64
        challenges = [BugReportService.generate_captcha() for _ in range(20)]
        tokens = [c.token for c in challenges]
        # All tokens are unique
        assert len(set(tokens)) == len(tokens)
        # Each token verifies only with its own answer
        for challenge in challenges:
            raw = base64.urlsafe_b64decode(challenge.token.encode()).decode()
            answer = raw.split(":")[0]
            assert BugReportService.verify_captcha(challenge.token, answer)


# ---------------------------------------------------------------------------
# Service DB tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_bug_report_authenticated(db_session):
    """Authenticated report stores user_id and message."""
    from uuid import uuid4
    from app.models.user import User
    from sqlalchemy import select

    user = User(
        id=uuid4(),
        email=f"bugreport-{uuid4()}@test.com",
        hashed_password="x",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    service = BugReportService(db_session)
    report = await service.create(
        message="Something is broken on this page",
        user_id=user.id,
        page_url="https://example.com/entities",
        user_agent="TestAgent/1.0",
    )

    assert report.user_id == user.id
    assert report.message == "Something is broken on this page"
    assert report.page_url == "https://example.com/entities"

    row = (await db_session.execute(
        select(BugReport).where(BugReport.id == report.id)
    )).scalar_one_or_none()
    assert row is not None


@pytest.mark.asyncio
async def test_create_bug_report_anonymous(db_session):
    """Anonymous report stores None for user_id."""
    service = BugReportService(db_session)
    report = await service.create(
        message="Anonymous bug report description",
        user_id=None,
        page_url=None,
        user_agent=None,
    )
    assert report.user_id is None
    assert report.message == "Anonymous bug report description"


@pytest.mark.asyncio
async def test_list_reports_returns_newest_first(db_session):
    """list_reports returns items ordered newest-first."""
    service = BugReportService(db_session)
    for i in range(3):
        await service.create(
            message=f"Report number {i} with enough text",
            user_id=None,
            page_url=None,
            user_agent=None,
        )

    items, total = await service.list_reports(page=1, page_size=10)
    assert total >= 3
    # Newest first
    for a, b in zip(items, items[1:]):
        assert a.created_at >= b.created_at
