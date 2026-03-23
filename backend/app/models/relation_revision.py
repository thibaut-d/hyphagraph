from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, JSON, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from uuid import UUID as PyUUID
from typing import Any
from app.models.base import Base, UUIDMixin


class RelationRevision(Base, UUIDMixin):
    """
    Represents a specific revision of a relation (claim/hyper-edge).

    Each relation can have multiple revisions over time.
    Only one revision per relation should have is_current=True.
    """
    __tablename__ = "relation_revisions"

    # Link to base relation
    relation_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("relations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Core fields
    kind: Mapped[str | None] = mapped_column(String)  # effect, mechanism, association
    direction: Mapped[str | None] = mapped_column(String)  # supports, contradicts, uncertain
    confidence: Mapped[float | None] = mapped_column(Float)  # strength of assertion by source

    # Contextual qualifiers
    scope: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # population, condition, etc.
    notes: Mapped[dict[str, str] | None] = mapped_column(JSON)  # i18n notes

    # Provenance tracking
    created_with_llm: Mapped[str | None] = mapped_column(String)  # e.g., "gpt-4", "claude-3"
    created_by_user_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Review status: 'draft' for LLM-created revisions pending human confirmation,
    # 'confirmed' for manually-entered or reviewed revisions.
    status: Mapped[str] = mapped_column(String, nullable=False, default="confirmed")

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
    relation = relationship("Relation", back_populates="revisions", lazy="raise")
    roles = relationship(
        "RelationRoleRevision",
        back_populates="relation_revision",
        cascade="all, delete-orphan",
        lazy="raise",
        passive_deletes=True,
    )
