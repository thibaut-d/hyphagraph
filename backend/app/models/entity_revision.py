from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, JSON, Boolean, ForeignKey, DateTime, Index, text
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from uuid import UUID as PyUUID
from app.models.base import Base, UUIDMixin


class EntityRevision(Base, UUIDMixin):
    """
    Represents a specific revision of an entity.

    Each entity can have multiple revisions over time.
    Only one revision per entity should have is_current=True.
    """
    __tablename__ = "entity_revisions"
    __table_args__ = (
        Index(
            "ix_entity_revisions_current_unique",
            "entity_id",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
        # Unique constraint: only one current revision can have a given slug
        Index(
            'ix_entity_revisions_slug_current_unique',
            'slug',
            unique=True,
            postgresql_where=text('is_current = true'),  # PostgreSQL partial index
            sqlite_where=text('is_current = 1'),  # SQLite uses 1 for true
        ),
    )

    # Link to base entity
    entity_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Optional UI category (for display purposes only, not semantic)
    ui_category_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ui_categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Core fields
    slug: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[dict[str, str] | None] = mapped_column(JSON)  # i18n: {"en": "...", "fr": "..."}

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
    entity = relationship("Entity", back_populates="revisions", lazy="raise")
