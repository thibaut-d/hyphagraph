"""
API endpoints for extraction review workflow.

Provides human-in-the-loop review interface for staged LLM extractions.
"""
import logging
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.dependencies.auth import get_current_user, get_current_active_superuser
from app.models.user import User
from app.schemas.staged_extraction import (
    StagedExtractionRead,
    StagedExtractionListResponse,
    ReviewDecisionRequest,
    BatchReviewRequest,
    BatchReviewResponse,
    ReviewStats,
    AutoCommitConfigRequest,
    MaterializationResult,
    StagedExtractionFilters,
)
from app.services.extraction_review_service import ExtractionReviewService
from app.utils.errors import AppException, ErrorCode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extraction-review", tags=["extraction-review"])


# =============================================================================
# Listing and Statistics
# =============================================================================

@router.get("/pending", response_model=StagedExtractionListResponse)
async def list_pending_extractions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    extraction_type: str | None = None,
    min_validation_score: float | None = Query(None, ge=0.0, le=1.0),
    has_flags: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List pending extractions awaiting review.

    Supports filtering by type, validation score, and flag presence.
    """
    service = ExtractionReviewService(db)

    filters = StagedExtractionFilters(
        status="pending",
        extraction_type=extraction_type,
        min_validation_score=min_validation_score,
        has_flags=has_flags,
        page=page,
        page_size=page_size,
    )

    extractions, total = await service.list_extractions(filters)

    return StagedExtractionListResponse(
        extractions=[StagedExtractionRead.model_validate(e) for e in extractions],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/stats", response_model=ReviewStats)
async def get_review_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get statistics about staged extractions.

    Includes counts by status, type, and quality metrics.
    """
    service = ExtractionReviewService(db)
    return await service.get_stats()


@router.get("/{extraction_id}", response_model=StagedExtractionRead)
async def get_extraction(
    extraction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get details of a specific staged extraction.
    """
    from sqlalchemy import select
    from app.models.staged_extraction import StagedExtraction

    result = await db.execute(
        select(StagedExtraction).where(StagedExtraction.id == extraction_id)
    )
    extraction = result.scalar_one_or_none()

    if not extraction:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Staged extraction not found",
            details=f"Staged extraction with ID '{extraction_id}' does not exist",
            context={"extraction_id": str(extraction_id)}
        )

    return StagedExtractionRead.model_validate(extraction)


# =============================================================================
# Review Actions
# =============================================================================

@router.post("/{extraction_id}/review", response_model=MaterializationResult)
async def review_extraction(
    extraction_id: UUID,
    decision: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Approve or reject a staged extraction.

    If approved, automatically materializes the extraction into the knowledge graph.
    """
    service = ExtractionReviewService(db)

    if decision.decision == "approve":
        result = await service.approve_extraction(
            extraction_id=extraction_id,
            reviewer_id=current_user.id,
            notes=decision.notes,
            auto_materialize=True,
        )
        return result
    else:  # reject
        success = await service.reject_extraction(
            extraction_id=extraction_id,
            reviewer_id=current_user.id,
            notes=decision.notes,
        )
        if success:
            return MaterializationResult(
                success=True,
                extraction_id=extraction_id,
                extraction_type="entity",  # Will be overwritten by actual type
            )
        else:
            raise AppException(
                status_code=400,
                error_code=ErrorCode.VALIDATION_ERROR,
                message="Failed to reject extraction",
                details="The extraction could not be rejected",
                context={"extraction_id": str(extraction_id)}
            )


@router.post("/batch-review", response_model=BatchReviewResponse)
async def batch_review_extractions(
    request: BatchReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Review multiple extractions at once.

    All extractions will receive the same decision and notes.
    """
    service = ExtractionReviewService(db)

    result = await service.batch_review(
        extraction_ids=request.extraction_ids,
        decision=request.decision,
        reviewer_id=current_user.id,
        notes=request.notes,
    )

    return BatchReviewResponse(**result)


# =============================================================================
# Auto-Commit Management
# =============================================================================

@router.post("/auto-commit", response_model=dict)
async def trigger_auto_commit(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Manually trigger auto-commit of all eligible pending extractions.

    Admin only. This will approve and materialize all high-confidence extractions
    that meet auto-commit criteria.
    """
    service = ExtractionReviewService(db)
    result = await service.auto_commit_eligible_extractions()

    return {
        "status": "success",
        **result,
    }


# =============================================================================
# Debugging and Admin
# =============================================================================

@router.get("/all", response_model=StagedExtractionListResponse)
async def list_all_extractions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    status: str | None = None,
    extraction_type: str | None = None,
    source_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    List all staged extractions with filtering.

    Admin only. Allows viewing extractions in any status.
    """
    service = ExtractionReviewService(db)

    filters = StagedExtractionFilters(
        status=status,
        extraction_type=extraction_type,
        source_id=source_id,
        page=page,
        page_size=page_size,
    )

    extractions, total = await service.list_extractions(filters)

    return StagedExtractionListResponse(
        extractions=[StagedExtractionRead.model_validate(e) for e in extractions],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.delete("/{extraction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staged_extraction(
    extraction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Delete a staged extraction.

    Admin only. Useful for removing erroneous or duplicate extractions.
    """
    from sqlalchemy import select
    from app.models.staged_extraction import StagedExtraction

    result = await db.execute(
        select(StagedExtraction).where(StagedExtraction.id == extraction_id)
    )
    extraction = result.scalar_one_or_none()

    if not extraction:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Staged extraction not found",
            details=f"Staged extraction with ID '{extraction_id}' does not exist",
            context={"extraction_id": str(extraction_id)}
        )

    await db.delete(extraction)
    await db.commit()

    logger.info(f"Deleted staged extraction {extraction_id}")
    return None
