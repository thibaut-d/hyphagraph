from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import Field

from app.schemas.base import Schema


class CaptchaChallenge(Schema):
    """Math CAPTCHA challenge for anonymous reporters."""

    token: str
    question: str


class BugReportCreate(Schema):
    """Payload for submitting a bug report."""

    message: str = Field(..., min_length=10, max_length=4000)
    page_url: Optional[str] = Field(None, max_length=2048)
    user_agent: Optional[str] = Field(None, max_length=512)
    # Required only for anonymous submissions
    captcha_token: Optional[str] = None
    captcha_answer: Optional[str] = None


class BugReportRead(Schema):
    """Admin-visible bug report."""

    id: UUID
    user_id: Optional[UUID] = None
    message: str
    page_url: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
