from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, JSON, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from uuid import UUID
from app.models.base import Base, UUIDMixin


class EntityRevision(Base, UUIDMixin):
    """
    Represents a specific revision of an entity.

    Each entity can have multiple revisions over time.
    Only one revision per entity should have is_current=True.
    """
    __tablename__ = "entity_revisions"

    # Link to base entity
    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Optional UI category (for display purposes only, not semantic)
    ui_category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ui_categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Core fields
    slug: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[dict | None] = mapped_column(JSON)  # i18n: {"en": "...", "fr": "..."}

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
    entity = relationship("Entity", back_populates="revisions")
