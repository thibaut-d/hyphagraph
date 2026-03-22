"""
API endpoints for the LLM-revision review queue.

Draft revisions (status='draft') are created by bulk_creation_service when
created_with_llm is set.  Humans confirm or discard them here.
"""
import logging
from fastapi import APIRouter, Depends, Query
from uuid import UUID

from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.revision_review_service import RevisionReviewService
from app.schemas.review import (
    DraftRevisionListResponse,
    ConfirmRevisionResponse,
    DiscardRevisionResponse,
)
from app.utils.errors import AppException, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review/revisions", tags=["revision-review"])

VALID_KINDS = {"entity", "relation", "source"}


def _get_service(db: AsyncSession = Depends(get_db)) -> RevisionReviewService:
    return RevisionReviewService(db)


@router.get("", response_model=DraftRevisionListResponse)
async def list_draft_revisions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    revision_kind: str | None = Query(default=None),
    service: RevisionReviewService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
):
    """List all LLM-generated draft revisions awaiting human review."""
    if revision_kind is not None and revision_kind not in VALID_KINDS:
        raise AppException(
            status_code=422,
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"revision_kind must be one of {sorted(VALID_KINDS)}",
        )
    return await service.list_drafts(page=page, page_size=page_size, revision_kind=revision_kind)


@router.get("/counts")
async def get_draft_counts(
    service: RevisionReviewService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Return count of draft revisions per kind."""
    return await service.get_draft_counts()


@router.post("/{revision_kind}/{revision_id}/confirm", response_model=ConfirmRevisionResponse)
async def confirm_revision(
    revision_kind: str,
    revision_id: UUID,
    service: RevisionReviewService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
):
    """Confirm a draft revision, marking it as authoritative."""
    if revision_kind not in VALID_KINDS:
        raise AppException(
            status_code=422,
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"revision_kind must be one of {sorted(VALID_KINDS)}",
        )
    ok = await service.confirm(revision_kind, revision_id)
    if not ok:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Draft revision not found",
            details=f"No draft {revision_kind} revision with id {revision_id}",
        )
    return ConfirmRevisionResponse(id=revision_id, revision_kind=revision_kind, status="confirmed")


@router.delete("/{revision_kind}/{revision_id}", response_model=DiscardRevisionResponse)
async def discard_revision(
    revision_kind: str,
    revision_id: UUID,
    service: RevisionReviewService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
):
    """Discard (delete) a draft revision."""
    if revision_kind not in VALID_KINDS:
        raise AppException(
            status_code=422,
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"revision_kind must be one of {sorted(VALID_KINDS)}",
        )
    ok = await service.discard(revision_kind, revision_id)
    if not ok:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Draft revision not found",
            details=f"No draft {revision_kind} revision with id {revision_id}",
        )
    return DiscardRevisionResponse(id=revision_id, revision_kind=revision_kind, deleted=True)
