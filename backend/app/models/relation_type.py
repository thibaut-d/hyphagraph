"""
RelationType model - Dynamic relation type vocabulary.

Stores the controlled vocabulary of relation types used in the knowledge graph.
Allows evolution of relation types over time while maintaining consistency.
"""
from sqlalchemy import String, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class RelationType(Base, TimestampMixin):
    """
    Relation type vocabulary entry.

    Stores allowed relation types with metadata for:
    - Deduplication (avoid creating similar types)
    - Guidance (help LLM choose correct type)
    - Validation (ensure consistency)
    - Evolution (add new types as needed)
    """

    __tablename__ = "relation_types"

    # Unique identifier (e.g., "treats", "measures", "causes")
    type_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # Human-readable label (i18n)
    label: Mapped[dict] = mapped_column(Text)  # {"en": "Treats", "fr": "Traite"}

    # Description for LLM guidance
    description: Mapped[str] = mapped_column(Text)  # "Drug/treatment treats disease/symptom"

    # Examples for LLM
    examples: Mapped[str | None] = mapped_column(Text, nullable=True)  # "aspirin treats migraine"

    # Synonyms/aliases to prevent duplicates
    aliases: Mapped[list[str] | None] = mapped_column(Text, nullable=True)  # ["cures", "heals"]

    # Whether this type is active/available
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Whether this type was system-created or user-created
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # Usage count (for analytics)
    usage_count: Mapped[int] = mapped_column(default=0)

    # Semantic category (for grouping)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "therapeutic", "causal", "diagnostic"

    __table_args__ = (
        Index('idx_relation_type_active', 'is_active'),
        Index('idx_relation_type_category', 'category'),
    )
