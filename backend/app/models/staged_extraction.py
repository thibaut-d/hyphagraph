"""
Database model for LLM extraction review metadata.

ALL extractions are materialized immediately and create a staged_extraction record.
The record tracks validation quality and review status.

Workflow:
- Extract → Validate → Materialize (always) → Create review metadata
- High confidence (score >= 0.9, no flags) → status="auto_verified"
- Uncertain (score < 0.9 or flags) → status="pending" (needs review)
- Human review changes status to "approved" or "rejected"
- Items remain visible in graph regardless of status

This provides async quality control without blocking knowledge extraction.
"""
from sqlalchemy import Column, String, Text, Float, Boolean, ForeignKey, Integer, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID as PyUUID, uuid4
from typing import Any, TYPE_CHECKING
import datetime
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.source import Source
    from app.models.user import User
    from app.models.entity import Entity
    from app.models.relation import Relation


class ExtractionStatus(str, enum.Enum):
    """Status of a staged extraction."""
    AUTO_VERIFIED = "auto_verified"  # High confidence, auto-approved and materialized
    PENDING = "pending"  # Materialized but awaiting human review
    APPROVED = "approved"  # Human reviewed and approved
    REJECTED = "rejected"  # Human reviewed and rejected (but still materialized)


class ExtractionType(str, enum.Enum):
    """Type of extraction."""
    ENTITY = "entity"
    RELATION = "relation"
    CLAIM = "claim"


class StagedExtraction(Base, UUIDMixin, TimestampMixin):
    """
    Review metadata for LLM extractions.

    ALL extractions create both an Entity/Relation AND a StagedExtraction record.
    This record tracks validation quality and human review status.
    Extractions are visible immediately; review is async quality control.
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
    source_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # LLM extraction data (serialized ExtractedEntity/Relation/Claim)
    extraction_data: Mapped[dict[str, Any]] = mapped_column(
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

    validation_flags: Mapped[list[str]] = mapped_column(
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
    reviewed_by: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True),
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
    materialized_entity_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
        comment="Entity created from this extraction (if type=entity)"
    )

    materialized_relation_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True),
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
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by])
    materialized_entity: Mapped["Entity | None"] = relationship(
        "Entity",
        foreign_keys=[materialized_entity_id],
        back_populates="source_extraction"
    )
    materialized_relation: Mapped["Relation | None"] = relationship(
        "Relation",
        foreign_keys=[materialized_relation_id],
        back_populates="source_extraction"
    )

    def __repr__(self) -> str:
        return (
            f"<StagedExtraction(id={self.id}, type={self.extraction_type}, "
            f"status={self.status}, score={self.validation_score:.2f})>"
        )
