from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, Index, UniqueConstraint, text, Boolean
from uuid import UUID
from app.models.base import Base, UUIDMixin, TimestampMixin


class EntityTerm(Base, UUIDMixin, TimestampMixin):
    """
    Represents different names/terms for an entity.

    Allows:
    - Multiple terms per entity (synonyms, aliases)
    - Language-specific terms
    - Display ordering (which term shows first)
    """
    __tablename__ = "entity_terms"

    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )

    term: Mapped[str] = mapped_column(String, nullable=False)

    # Language code (ISO 639-1) or NULL for international terms (chemical names, codes, etc.)
    language: Mapped[str | None] = mapped_column(String(10))

    # Display order (smaller = shown first), nullable
    display_order: Mapped[int | None] = mapped_column(Integer)

    # At most one display name per language, plus at most one international display name.
    is_display_name: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    # Non-display terms can be ordinary aliases or abbreviations/acronyms.
    term_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="alias", server_default=text("'alias'"))

    # Relationships
    entity = relationship("Entity", back_populates="terms")

    __table_args__ = (
        # Composite unique constraint: same term can't appear twice for same entity/language
        UniqueConstraint('entity_id', 'term', 'language', name='uq_entity_term_language'),
        # PostgreSQL and SQLite both treat NULLs as distinct in composite unique constraints,
        # so guard the language=NULL case explicitly.
        Index(
            "ix_entity_terms_entity_term_null_language_unique",
            "entity_id",
            "term",
            unique=True,
            postgresql_where=text("language IS NULL"),
            sqlite_where=text("language IS NULL"),
        ),
        Index(
            "ix_entity_terms_display_name_per_entity_language",
            "entity_id",
            "language",
            unique=True,
            postgresql_where=text("is_display_name = true AND language IS NOT NULL"),
            sqlite_where=text("is_display_name = 1 AND language IS NOT NULL"),
        ),
        Index(
            "ix_entity_terms_display_name_per_entity_international",
            "entity_id",
            unique=True,
            postgresql_where=text("is_display_name = true AND language IS NULL"),
            sqlite_where=text("is_display_name = 1 AND language IS NULL"),
        ),
    )
