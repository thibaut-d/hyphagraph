"""
Service for bug reports and server-side math CAPTCHA.

CAPTCHA design:
  - Generate two single-digit operands and a random +/- operation.
  - Sign the expected answer + expiry with HMAC-SHA256(SECRET_KEY).
  - Token format (base64url): "{answer}:{expiry_unix}:{hex_hmac}"
  - 10-minute validity window.
  - Clients submit the token + their plaintext answer; we re-derive the HMAC
    and compare.
"""
import hashlib
import hmac
import logging
import random
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.bug_report import BugReport
from app.schemas.bug_report import BugReportRead, CaptchaChallenge

logger = logging.getLogger(__name__)

_CAPTCHA_TTL = 600  # 10 minutes


class BugReportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # CAPTCHA
    # ------------------------------------------------------------------

    @staticmethod
    def generate_captcha() -> CaptchaChallenge:
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        if random.choice([True, False]) and a >= b:
            question = f"What is {a} - {b}?"
            answer = a - b
        else:
            question = f"What is {a} + {b}?"
            answer = a + b

        expiry = int(time.time()) + _CAPTCHA_TTL
        token = BugReportService._sign_captcha(str(answer), expiry)
        return CaptchaChallenge(token=token, question=question)

    @staticmethod
    def verify_captcha(token: str, answer: str) -> bool:
        """Return True if the token is valid, unexpired, and the answer matches."""
        try:
            raw = urlsafe_b64decode(token.encode()).decode()
            expected_answer, expiry_str, stored_sig = raw.split(":", 2)
        except Exception:
            return False

        # Check expiry
        if int(time.time()) > int(expiry_str):
            return False

        # Verify HMAC
        expected_sig = BugReportService._hmac(expected_answer, int(expiry_str))
        if not hmac.compare_digest(expected_sig, stored_sig):
            return False

        # Compare answer (strip whitespace, case-insensitive for robustness)
        return answer.strip() == expected_answer

    @staticmethod
    def _sign_captcha(answer: str, expiry: int) -> str:
        sig = BugReportService._hmac(answer, expiry)
        raw = f"{answer}:{expiry}:{sig}"
        return urlsafe_b64encode(raw.encode()).decode()

    @staticmethod
    def _hmac(answer: str, expiry: int) -> str:
        msg = f"{answer}:{expiry}".encode()
        return hmac.new(settings.SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(
        self,
        message: str,
        user_id: UUID | None,
        page_url: str | None,
        user_agent: str | None,
    ) -> BugReport:
        report = BugReport(
            user_id=user_id,
            message=message,
            page_url=page_url,
            user_agent=user_agent,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        logger.info("Bug report created: id=%s user_id=%s", report.id, user_id)
        return report

    # ------------------------------------------------------------------
    # List (admin)
    # ------------------------------------------------------------------

    async def list_reports(
        self, page: int = 1, page_size: int = 50
    ) -> tuple[list[BugReportRead], int]:
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(BugReport).order_by(BugReport.created_at.desc()).offset(offset).limit(page_size)
        )
        rows = result.scalars().all()
        from sqlalchemy import func
        total = (await self.db.scalar(select(func.count()).select_from(BugReport))) or 0
        items = [
            BugReportRead(
                id=r.id,
                user_id=r.user_id,
                message=r.message,
                page_url=r.page_url,
                user_agent=r.user_agent,
                created_at=r.created_at,
            )
            for r in rows
        ]
        return items, total
