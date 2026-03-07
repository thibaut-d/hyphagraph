"""
Database model for staged LLM extractions pending human review.

Staged extractions are created when:
1. Validation confidence is below auto-commit threshold
2. User explicitly requests review-before-commit
3. Extraction has validation flags that require attention

Workflow:
- Extract → Validate → Route (auto-commit vs staging)
- Staged extractions can be: approved, rejected, or edited
- Approval materializes the extraction into the knowledge graph
"""
from sqlalchemy import Column, String, Text, Float, Boolean, ForeignKey, Integer, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4
import datetime
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin


class ExtractionStatus(str, enum.Enum):
    """Status of a staged extraction."""
    PENDING = "pending"  # Awaiting review
    APPROVED = "approved"  # Approved for materialization
    REJECTED = "rejected"  # Rejected, won't be materialized
    MATERIALIZED = "materialized"  # Already committed to knowledge graph


class ExtractionType(str, enum.Enum):
    """Type of extraction."""
    ENTITY = "entity"
    RELATION = "relation"
    CLAIM = "claim"


class StagedExtraction(Base, UUIDMixin, TimestampMixin):
    """
    Staged extraction pending human review.

    Stores LLM extractions with validation metadata, allowing human
    verification before committing to the knowledge graph.
    """
    __tablename__ = "staged_extractions"

    # Core fields
    extraction_type: Mapped[ExtractionType] = mapped_column(
        SQLEnum(ExtractionType, native_enum=False),
        nullable=False,
        index=True
    )

    status: Mapped[ExtractionStatus] = mapped_column(
        SQLEnum(ExtractionStatus, native_enum=False),
        nullable=False,
        default=ExtractionStatus.PENDING,
        index=True
    )

    # Source tracking
    source_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # LLM extraction data (serialized ExtractedEntity/Relation/Claim)
    extraction_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="Original LLM extraction (ExtractedEntity/Relation/Claim schema)"
    )

    # Validation metadata
    validation_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True,
        comment="Overall validation score (0.0-1.0)"
    )

    confidence_adjustment: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        comment="Confidence multiplier from validation (0.0-1.0)"
    )

    validation_flags: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="List of validation issues found"
    )

    matched_span: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Matched text span from source (if found)"
    )

    # LLM metadata
    llm_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="LLM model used for extraction"
    )

    llm_provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="LLM provider (anthropic, openai, etc.)"
    )

    # Review metadata
    reviewed_by: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who reviewed this extraction"
    )

    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp of review"
    )

    review_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human notes from review"
    )

    # Materialization tracking
    materialized_entity_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        comment="Entity created from this extraction (if type=entity)"
    )

    materialized_relation_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("relations.id", ondelete="SET NULL"),
        nullable=True,
        comment="Relation created from this extraction (if type=relation)"
    )

    # Auto-commit decision tracking
    auto_commit_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this extraction met auto-commit criteria"
    )

    auto_commit_threshold: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Threshold used for auto-commit decision"
    )

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="staged_extractions")
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewed_by])
    materialized_entity: Mapped["Entity"] = relationship(
        "Entity",
        foreign_keys=[materialized_entity_id],
        back_populates="source_extraction"
    )
    materialized_relation: Mapped["Relation"] = relationship(
        "Relation",
        foreign_keys=[materialized_relation_id],
        back_populates="source_extraction"
    )

    def __repr__(self) -> str:
        return (
            f"<StagedExtraction(id={self.id}, type={self.extraction_type}, "
            f"status={self.status}, score={self.validation_score:.2f})>"
        )
