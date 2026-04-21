"""
EntityCategory model - Dynamic entity category vocabulary.

Stores the controlled vocabulary of entity categories used during extraction.
Mirrors the RelationType pattern so admins can manage categories without code changes.
"""
from sqlalchemy import JSON, String, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class EntityCategory(Base, TimestampMixin):
    """
    Entity category vocabulary entry.

    Stores allowed entity categories with metadata for:
    - LLM prompt generation (description helps the model choose correctly)
    - Admin management (create, rename, deactivate without deploys)
    - Analytics (usage_count tracks extraction frequency)
    """

    __tablename__ = "entity_categories"

    # Unique identifier (e.g., "drug", "disease", "outcome")
    category_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Human-readable label (i18n)
    label: Mapped[dict] = mapped_column(JSON)  # {"en": "Drug", "fr": "Médicament"}

    # Description for LLM guidance
    description: Mapped[str] = mapped_column(String)

    # Examples for LLM
    examples: Mapped[str | None] = mapped_column(String, nullable=True)

    # Whether this category is active/available
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Whether this category was system-created or user-created
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)

    # Usage count (for analytics)
    usage_count: Mapped[int] = mapped_column(default=0)

    __table_args__ = (
        Index("idx_entity_category_active", "is_active"),
    )
