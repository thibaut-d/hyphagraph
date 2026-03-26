"""
Bug report API.

  GET  /bug-reports/captcha      — math CAPTCHA for anonymous reporters
  POST /bug-reports               — submit a report (auth optional)
  GET  /bug-reports               — list all reports (superuser only)
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_active_superuser, get_optional_current_user
from app.models.user import User
from app.schemas.bug_report import BugReportCreate, BugReportRead, CaptchaChallenge
from app.services.bug_report_service import BugReportService

router = APIRouter(prefix="/bug-reports", tags=["bug-reports"])


def _get_service(db: AsyncSession = Depends(get_db)) -> BugReportService:
    return BugReportService(db)


@router.get("/captcha", response_model=CaptchaChallenge)
def get_captcha():
    """Return a math CAPTCHA challenge for anonymous bug reporters."""
    return BugReportService.generate_captcha()


@router.post("", status_code=status.HTTP_201_CREATED, response_model=BugReportRead)
async def submit_bug_report(
    payload: BugReportCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    service: BugReportService = Depends(_get_service),
):
    """
    Submit a bug report.

    - Authenticated users: no CAPTCHA required.
    - Anonymous users: must supply captcha_token + captcha_answer.
    """
    if current_user is None:
        if not payload.captcha_token or not payload.captcha_answer:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="captcha_token and captcha_answer are required for anonymous submissions",
            )
        if not BugReportService.verify_captcha(payload.captcha_token, payload.captcha_answer):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired CAPTCHA answer",
            )

    user_id: UUID | None = current_user.id if current_user else None
    report = await service.create(
        message=payload.message,
        user_id=user_id,
        page_url=payload.page_url,
        user_agent=payload.user_agent,
    )
    return BugReportRead(
        id=report.id,
        user_id=report.user_id,
        message=report.message,
        page_url=report.page_url,
        user_agent=report.user_agent,
        created_at=report.created_at,
    )


@router.get("", response_model=list[BugReportRead])
async def list_bug_reports(
    page: int = 1,
    page_size: int = 50,
    _: User = Depends(get_current_active_superuser),
    service: BugReportService = Depends(_get_service),
):
    """List all bug reports. Superuser only."""
    items, _ = await service.list_reports(page=page, page_size=page_size)
    return items
