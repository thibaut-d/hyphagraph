"""
API endpoints for extraction review workflow.

Provides human-in-the-loop review interface for staged LLM extractions.
"""
import logging
from fastapi import APIRouter, Depends, Query, status
from uuid import UUID
from pydantic import BaseModel

from app.api.service_dependencies import get_extraction_review_service
from app.dependencies.auth import get_current_active_superuser
from app.models.user import User
from app.schemas.staged_extraction import (
    StagedExtractionRead,
    StagedExtractionListResponse,
    ReviewDecisionRequest,
    BatchReviewRequest,
    AutoCommitResponse,
    BatchReviewResponse,
    ReviewStats,
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
    filters: StagedExtractionFilters = Depends(),
    service: ExtractionReviewService = Depends(get_extraction_review_service),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    List pending extractions awaiting review.

    Supports filtering by type, validation score, and flag presence.
    """
    pending_filters = filters.model_copy(update={"status": "pending"})

    extractions, total = await service.list_extractions(pending_filters)

    return StagedExtractionListResponse(
        extractions=[StagedExtractionRead.model_validate(e) for e in extractions],
        total=total,
        page=pending_filters.page,
        page_size=pending_filters.page_size,
        has_more=(pending_filters.page * pending_filters.page_size) < total,
    )


@router.get("/stats", response_model=ReviewStats)
async def get_review_stats(
    service: ExtractionReviewService = Depends(get_extraction_review_service),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Get statistics about staged extractions.

    Includes counts by status, type, and quality metrics.
    """
    return await service.get_stats()


@router.get("/all", response_model=StagedExtractionListResponse)
async def list_all_extractions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    status: str | None = None,
    extraction_type: str | None = None,
    source_id: UUID | None = None,
    service: ExtractionReviewService = Depends(get_extraction_review_service),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    List all staged extractions with filtering.

    Admin only. Allows viewing extractions in any status.
    """
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


@router.get("/{extraction_id}", response_model=StagedExtractionRead)
async def get_extraction(
    extraction_id: UUID,
    service: ExtractionReviewService = Depends(get_extraction_review_service),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Get details of a specific staged extraction.
    """
    extraction = await service.get_extraction(extraction_id)

    if not extraction:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Staged extraction not found",
            details=f"Staged extraction with ID '{extraction_id}' does not exist",
            context={"extraction_id": str(extraction_id)}
        )

    return StagedExtractionRead.model_validate(extraction)


class RelationTypeCorrectionRequest(BaseModel):
    relation_type: str


@router.patch("/{extraction_id}/relation-type", response_model=StagedExtractionRead)
async def correct_relation_type(
    extraction_id: UUID,
    request: RelationTypeCorrectionRequest,
    service: ExtractionReviewService = Depends(get_extraction_review_service),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Correct the relation_type of a pending staged relation extraction.

    Updates extraction_data.relation_type in-place. Intended for curators
    who want to reassign an 'other' relation (or a model-invented type) to
    an existing controlled-vocabulary type before approving.
    """
    extraction = await service.get_extraction(extraction_id)
    if not extraction:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Staged extraction not found",
            context={"extraction_id": str(extraction_id)},
        )
    if extraction.extraction_type != "relation":
        raise AppException(
            status_code=400,
            error_code=ErrorCode.VALIDATION_ERROR,
            message="relation_type correction only applies to relation extractions",
        )

    data = dict(extraction.extraction_data or {})
    data["relation_type"] = request.relation_type
    extraction.extraction_data = data
    await service.db.commit()
    await service.db.refresh(extraction)
    return StagedExtractionRead.model_validate(extraction)


# =============================================================================
# Review Actions
# =============================================================================

@router.post("/{extraction_id}/review", response_model=MaterializationResult)
async def review_extraction(
    extraction_id: UUID,
    decision: ReviewDecisionRequest,
    service: ExtractionReviewService = Depends(get_extraction_review_service),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Approve or reject a staged extraction.

    If approved, automatically materializes the extraction into the knowledge graph.
    """
    if decision.decision == "approve":
        result = await service.approve_extraction(
            extraction_id=extraction_id,
            reviewer_id=current_user.id,
            notes=decision.notes,
            auto_materialize=True,
        )
        return result
    else:  # reject
        staged = await service.get_extraction(extraction_id)
        if not staged:
            raise AppException(
                status_code=404,
                error_code=ErrorCode.NOT_FOUND,
                message="Staged extraction not found",
                details=f"Staged extraction with ID '{extraction_id}' does not exist",
                context={"extraction_id": str(extraction_id)}
            )
        success = await service.reject_extraction(
            extraction_id=extraction_id,
            reviewer_id=current_user.id,
            notes=decision.notes,
        )
        if success:
            return MaterializationResult(
                success=True,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
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
    service: ExtractionReviewService = Depends(get_extraction_review_service),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Review multiple extractions at once.

    All extractions will receive the same decision and notes.
    """
    result = await service.batch_review(
        extraction_ids=request.extraction_ids,
        decision=request.decision,
        reviewer_id=current_user.id,
        notes=request.notes,
    )

    return result


# =============================================================================
# Auto-Commit Management
# =============================================================================

@router.post("/auto-commit", response_model=AutoCommitResponse)
async def trigger_auto_commit(
    service: ExtractionReviewService = Depends(get_extraction_review_service),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Manually trigger auto-commit of all eligible pending extractions.

    Admin only. This will approve and materialize all high-confidence extractions
    that meet auto-commit criteria.
    """
    return await service.auto_commit_eligible_extractions()


@router.delete("/{extraction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staged_extraction(
    extraction_id: UUID,
    service: ExtractionReviewService = Depends(get_extraction_review_service),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    Delete a staged extraction.

    Admin only. Useful for removing erroneous or duplicate extractions.
    """
    deleted = await service.delete_extraction(extraction_id)
    if not deleted:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Staged extraction not found",
            details=f"Staged extraction with ID '{extraction_id}' does not exist",
            context={"extraction_id": str(extraction_id)}
        )

    return None
