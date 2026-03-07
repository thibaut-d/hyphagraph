"""
Pydantic schemas for staged extraction review workflow.

Defines request/response models for:
- Viewing staged extractions
- Approving/rejecting extractions
- Batch review operations
- Review statistics
"""
from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from typing import Literal

from app.llm.schemas import ExtractedEntity, ExtractedRelation, ExtractedClaim


# =============================================================================
# Enums
# =============================================================================

ExtractionStatusLiteral = Literal["pending", "approved", "rejected", "materialized"]
ExtractionTypeLiteral = Literal["entity", "relation", "claim"]


# =============================================================================
# Response Models
# =============================================================================

class StagedExtractionRead(BaseModel):
    """
    Public read schema for a staged extraction.

    Includes all metadata needed for human review.
    """
    id: UUID4
    extraction_type: ExtractionTypeLiteral
    status: ExtractionStatusLiteral

    # Source tracking
    source_id: UUID4

    # Extraction data (polymorphic based on extraction_type)
    extraction_data: ExtractedEntity | ExtractedRelation | ExtractedClaim

    # Validation metadata
    validation_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall validation score"
    )
    confidence_adjustment: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence multiplier from validation"
    )
    validation_flags: list[str] = Field(
        default_factory=list,
        description="Validation issues found"
    )
    matched_span: str | None = Field(
        None,
        description="Matched text from source"
    )

    # LLM metadata
    llm_model: str | None = None
    llm_provider: str | None = None

    # Review metadata
    reviewed_by: UUID4 | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None

    # Materialization tracking
    materialized_entity_id: UUID4 | None = None
    materialized_relation_id: UUID4 | None = None

    # Auto-commit metadata
    auto_commit_eligible: bool
    auto_commit_threshold: float | None = None

    # Timestamps
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "extraction_type": "entity",
                "status": "pending",
                "source_id": "987fcdeb-51a2-43f7-9c5d-8b3a7c9e4f6a",
                "extraction_data": {
                    "slug": "duloxetine",
                    "category": "drug",
                    "confidence": "high",
                    "text_span": "Duloxetine is an FDA-approved medication"
                },
                "validation_score": 0.85,
                "confidence_adjustment": 0.9,
                "validation_flags": ["fuzzy_match"],
                "matched_span": "Duloxetine is an FDA-approved medication",
                "auto_commit_eligible": False,
                "created_at": "2026-03-07T14:30:00Z"
            }
        }
    }


class StagedExtractionListResponse(BaseModel):
    """Response for list endpoint with pagination."""
    extractions: list[StagedExtractionRead]
    total: int
    page: int
    page_size: int
    has_more: bool


class ReviewStats(BaseModel):
    """Statistics about staged extractions."""
    total_pending: int
    total_approved: int
    total_rejected: int
    total_auto_verified: int

    # Breakdown by type
    pending_entities: int
    pending_relations: int
    pending_claims: int

    # Quality metrics
    avg_validation_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average validation score of pending extractions"
    )
    high_confidence_count: int = Field(
        ...,
        description="Number of pending extractions with validation_score >= 0.9"
    )
    flagged_count: int = Field(
        ...,
        description="Number of pending extractions with validation flags"
    )


# =============================================================================
# Request Models
# =============================================================================

class ReviewDecisionRequest(BaseModel):
    """Request to approve or reject a staged extraction."""
    decision: Literal["approve", "reject"] = Field(
        ...,
        description="Review decision"
    )
    notes: str | None = Field(
        None,
        max_length=1000,
        description="Optional review notes"
    )


class BatchReviewRequest(BaseModel):
    """Request to review multiple extractions at once."""
    extraction_ids: list[UUID4] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="IDs of extractions to review"
    )
    decision: Literal["approve", "reject"]
    notes: str | None = Field(
        None,
        max_length=1000,
        description="Optional notes applied to all"
    )


class BatchReviewResponse(BaseModel):
    """Response from batch review operation."""
    total_requested: int
    succeeded: int
    failed: int
    failed_ids: list[UUID4] = Field(
        default_factory=list,
        description="IDs that failed to process"
    )
    materialized_entities: list[UUID4] = Field(
        default_factory=list,
        description="Entity IDs created from approved extractions"
    )
    materialized_relations: list[UUID4] = Field(
        default_factory=list,
        description="Relation IDs created from approved extractions"
    )


class AutoCommitConfigRequest(BaseModel):
    """Request to configure auto-commit behavior."""
    enabled: bool = Field(
        ...,
        description="Whether to enable auto-commit"
    )
    threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Minimum validation score for auto-commit"
    )
    require_no_flags: bool = Field(
        default=True,
        description="Whether to require zero validation flags for auto-commit"
    )


class MaterializationResult(BaseModel):
    """Result of materializing a staged extraction."""
    success: bool
    extraction_id: UUID4
    extraction_type: ExtractionTypeLiteral
    materialized_entity_id: UUID4 | None = None
    materialized_relation_id: UUID4 | None = None
    error: str | None = None


# =============================================================================
# Filter Models
# =============================================================================

class StagedExtractionFilters(BaseModel):
    """Query filters for listing staged extractions."""
    status: ExtractionStatusLiteral | None = None
    extraction_type: ExtractionTypeLiteral | None = None
    source_id: UUID4 | None = None
    min_validation_score: float | None = Field(None, ge=0.0, le=1.0)
    max_validation_score: float | None = Field(None, ge=0.0, le=1.0)
    has_flags: bool | None = Field(
        None,
        description="Filter for extractions with/without validation flags"
    )
    auto_commit_eligible: bool | None = None

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)

    # Sorting
    sort_by: Literal["created_at", "validation_score", "confidence_adjustment"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"
