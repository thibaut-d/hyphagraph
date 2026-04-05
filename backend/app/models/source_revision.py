from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    String,
    Integer,
    Float,
    JSON,
    Boolean,
    ForeignKey,
    DateTime,
    Text,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from uuid import UUID as PyUUID
from typing import Any
from app.models.base import Base, UUIDMixin


class SourceRevision(Base, UUIDMixin):
    """
    Represents a specific revision of a source.

    Each source can have multiple revisions over time.
    Only one revision per source should have is_current=True.
    """
    __tablename__ = "source_revisions"
    __table_args__ = (
        CheckConstraint(
            "trust_level IS NULL OR (trust_level >= 0 AND trust_level <= 1)",
            name="ck_source_revisions_trust_level",
        ),
        Index(
            "ix_source_revisions_current_unique",
            "source_id",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
    )

    # Link to base source
    source_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Core fields
    kind: Mapped[str] = mapped_column(String, nullable=False)  # study, review, guideline, case_report
    title: Mapped[str] = mapped_column(String, nullable=False)
    authors: Mapped[list[str] | None] = mapped_column(JSON)  # Stored as JSON array for cross-DB compatibility
    year: Mapped[int | None] = mapped_column(Integer)
    origin: Mapped[str | None] = mapped_column(String)  # journal, organization, publisher
    url: Mapped[str] = mapped_column(String, nullable=False)
    trust_level: Mapped[float | None] = mapped_column(Float)
    calculated_trust_level: Mapped[float | None] = mapped_column(Float, nullable=True)

    # i18n and metadata
    summary: Mapped[dict[str, str] | None] = mapped_column(JSON)  # i18n: {"en": "...", "fr": "..."}
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # doi, pubmed_id, etc.

    # Provenance tracking
    created_with_llm: Mapped[str | None] = mapped_column(String)  # e.g., "gpt-4", "claude-3"
    created_by_user_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Document content (for uploaded PDFs/text files)
    document_text: Mapped[str | None] = mapped_column(Text)  # Full extracted text
    document_format: Mapped[str | None] = mapped_column(String)  # pdf, txt, etc.
    document_file_name: Mapped[str | None] = mapped_column(String)  # Original filename
    document_extracted_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True)
    )  # When text was extracted

    # Review status: 'draft' for LLM-created revisions pending human confirmation,
    # 'confirmed' for manually-entered or reviewed revisions.
    status: Mapped[str] = mapped_column(String, nullable=False, default="confirmed")

    # LLM provenance review status (NULL for human-authored rows):
    #   'pending_review'  — LLM-created, awaiting human confirmation
    #   'auto_verified'   — LLM-created, passed automated quality check
    #   'confirmed'       — LLM-created, explicitly confirmed by a human
    llm_review_status: Mapped[str | None] = mapped_column(String, nullable=True)

    # Confirmation provenance
    confirmed_by_user_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Revision metadata
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    source = relationship("Source", back_populates="revisions", lazy="raise")
