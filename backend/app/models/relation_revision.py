from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, JSON, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from uuid import UUID
from app.models.base import Base, UUIDMixin


class RelationRevision(Base, UUIDMixin):
    """
    Represents a specific revision of a relation (claim/hyper-edge).

    Each relation can have multiple revisions over time.
    Only one revision per relation should have is_current=True.
    """
    __tablename__ = "relation_revisions"

    # Link to base relation
    relation_id: Mapped[UUID] = mapped_column(
        ForeignKey("relations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Core fields
    kind: Mapped[str | None] = mapped_column(String)  # effect, mechanism, association
    direction: Mapped[str | None] = mapped_column(String)  # supports, contradicts, uncertain
    confidence: Mapped[float | None] = mapped_column(Float)  # strength of assertion by source

    # Contextual qualifiers
    scope: Mapped[dict | None] = mapped_column(JSON)  # population, condition, etc.
    notes: Mapped[dict | None] = mapped_column(JSON)  # i18n notes

    # Provenance tracking
    created_with_llm: Mapped[str | None] = mapped_column(String)  # e.g., "gpt-4", "claude-3"
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Revision metadata
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    relation = relationship("Relation", back_populates="revisions")
    roles = relationship(
        "RelationRoleRevision",
        back_populates="relation_revision",
        cascade="all, delete-orphan",
    )
