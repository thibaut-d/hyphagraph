"""
Pydantic schemas for staged extraction review workflow.

Defines request/response models for:
- Viewing staged extractions
- Approving/rejecting extractions
- Batch review operations
- Review statistics
"""

from typing import Literal
from uuid import UUID
from datetime import datetime

from pydantic import AliasChoices, ConfigDict, Field

from app.schemas.base import Schema
from app.schemas.common_types import JsonObject, JsonScalar


# =============================================================================
# Enums
# =============================================================================

ExtractionStatusLiteral = Literal["auto_verified", "pending", "approved", "rejected"]
ExtractionTypeLiteral = Literal["entity", "relation"]


# =============================================================================
# Response Models
# =============================================================================


class StagedExtractedEntityRead(Schema):
    """
    Review-safe entity payload.

    Staged review data must remain listable even when an extracted draft is
    incomplete or no longer matches the stricter write-time extraction schema.
    """

    model_config = ConfigDict(extra="allow")

    slug: str | None = None
    summary: str | None = None
    category: str | None = None
    confidence: str | None = None
    text_span: str | None = None


class StagedExtractedRoleRead(Schema):
    model_config = ConfigDict(extra="allow")

    entity_slug: str | None = None
    role_type: str | None = None


class StagedExtractedRelationEvidenceContextRead(Schema):
    model_config = ConfigDict(extra="allow")

    statement_kind: str | None = None
    finding_polarity: str | None = None
    evidence_strength: str | None = None
    study_design: str | None = None
    sample_size: int | None = None
    sample_size_text: str | None = None
    assertion_text: str | None = None
    methodology_text: str | None = None
    statistical_support: str | None = None


class StagedExtractedRelationRead(Schema):
    model_config = ConfigDict(extra="allow")

    relation_type: str | None = None
    roles: list[StagedExtractedRoleRead] = Field(default_factory=list)
    confidence: str | None = None
    text_span: str | None = None
    notes: str | None = None
    scope: JsonObject | None = None
    evidence_context: StagedExtractedRelationEvidenceContextRead | None = Field(
        None,
        validation_alias=AliasChoices("evidence_context", "study_context"),
    )

    @property
    def study_context(self) -> StagedExtractedRelationEvidenceContextRead | None:
        return self.evidence_context


class StagedExtractionRead(Schema):
    """
    Public read schema for a staged extraction.

    Includes all metadata needed for human review.
    """

    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        validate_assignment=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "extraction_type": "entity",
                "status": "pending",
                "source_id": "987fcdeb-51a2-43f7-9c5d-8b3a7c9e4f6a",
                "extraction_data": {
                    "slug": "duloxetine",
                    "category": "drug",
                    "confidence": "high",
                    "text_span": "Duloxetine is an FDA-approved medication",
                },
                "validation_score": 0.85,
                "confidence_adjustment": 0.9,
                "validation_flags": ["fuzzy_match"],
                "matched_span": "Duloxetine is an FDA-approved medication",
                "auto_commit_eligible": False,
                "created_at": "2026-03-07T14:30:00Z",
            }
        },
    )

    id: UUID
    extraction_type: ExtractionTypeLiteral
    status: ExtractionStatusLiteral

    # Source tracking
    source_id: UUID

    # Extraction data (polymorphic based on extraction_type). This read contract is
    # intentionally looser than the write-time extraction schema so pending review
    # rows remain visible even when they contain incomplete or drifted payloads.
    extraction_data: (
        StagedExtractedEntityRead
        | StagedExtractedRelationRead
        | dict[str, JsonScalar | list[object] | dict[str, object] | None]
    )

    # Validation metadata
    validation_score: float = Field(..., ge=0.0, le=1.0, description="Overall validation score")
    confidence_adjustment: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence multiplier from validation"
    )
    validation_flags: list[str] = Field(default_factory=list, description="Validation issues found")
    matched_span: str | None = Field(None, description="Matched text from source")

    # LLM metadata
    llm_model: str | None = None
    llm_provider: str | None = None

    # Review metadata
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None

    # Materialization tracking
    materialized_entity_id: UUID | None = None
    materialized_relation_id: UUID | None = None

    # Auto-commit metadata
    auto_commit_eligible: bool
    auto_commit_threshold: float | None = None
    auto_approved: bool = False

    # Timestamps
    created_at: datetime


class StagedExtractionListResponse(Schema):
    """Response for list endpoint with pagination."""

    extractions: list[StagedExtractionRead]
    total: int
    page: int
    page_size: int
    has_more: bool


class ReviewStats(Schema):
    """Statistics about staged extractions."""

    total_pending: int
    total_approved: int
    total_rejected: int
    total_auto_verified: int

    # Breakdown by type
    pending_entities: int
    pending_relations: int

    # Quality metrics
    avg_validation_score: float = Field(
        ..., ge=0.0, le=1.0, description="Average validation score of pending extractions"
    )
    high_confidence_count: int = Field(
        ..., description="Number of pending extractions with validation_score >= 0.9"
    )
    flagged_count: int = Field(
        ..., description="Number of pending extractions with validation flags"
    )


# =============================================================================
# Request Models
# =============================================================================


class ReviewDecisionRequest(Schema):
    """Request to approve or reject a staged extraction."""

    decision: Literal["approve", "reject"] = Field(..., description="Review decision")
    notes: str | None = Field(None, max_length=1000, description="Optional review notes")


class BatchReviewRequest(Schema):
    """Request to review multiple extractions at once."""

    extraction_ids: list[UUID] = Field(
        ..., min_length=1, max_length=100, description="IDs of extractions to review"
    )
    decision: Literal["approve", "reject"]
    notes: str | None = Field(None, max_length=1000, description="Optional notes applied to all")


class BatchReviewResponse(Schema):
    """Response from batch review operation."""

    total_requested: int
    succeeded: int
    failed: int
    failed_ids: list[UUID] = Field(default_factory=list, description="IDs that failed to process")
    materialized_entities: list[UUID] = Field(
        default_factory=list, description="Entity IDs created from approved extractions"
    )
    materialized_relations: list[UUID] = Field(
        default_factory=list, description="Relation IDs created from approved extractions"
    )


class AutoCommitResponse(Schema):
    """Response from manually triggering auto-commit."""

    status: Literal["success"]
    auto_committed: int
    failed: int = 0
    total_eligible: int = 0
    message: str | None = None


class AutoCommitConfigRequest(Schema):
    """Request to configure auto-commit behavior."""

    enabled: bool = Field(..., description="Whether to enable auto-commit")
    threshold: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Minimum validation score for auto-commit"
    )
    require_no_flags: bool = Field(
        default=True, description="Whether to require zero validation flags for auto-commit"
    )


class MaterializationResult(Schema):
    """Result of materializing a staged extraction."""

    success: bool
    extraction_id: UUID
    extraction_type: ExtractionTypeLiteral
    materialized_entity_id: UUID | None = None
    materialized_relation_id: UUID | None = None
    error: str | None = None


# =============================================================================
# Filter Models
# =============================================================================


class StagedExtractionFilters(Schema):
    """Query filters for listing staged extractions."""

    status: ExtractionStatusLiteral | None = None
    extraction_type: ExtractionTypeLiteral | None = None
    source_id: UUID | None = None
    min_validation_score: float | None = Field(None, ge=0.0, le=1.0)
    max_validation_score: float | None = Field(None, ge=0.0, le=1.0)
    has_flags: bool | None = Field(
        None, description="Filter for extractions with/without validation flags"
    )
    auto_commit_eligible: bool | None = None
    auto_approved: bool | None = None

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)

    # Sorting
    sort_by: Literal["created_at", "validation_score", "confidence_adjustment"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"
