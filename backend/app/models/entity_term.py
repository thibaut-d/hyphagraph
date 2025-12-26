from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from uuid import UUID
from app.models.base import Base, UUIDMixin


class EntityTerm(Base, UUIDMixin):
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

    # Relationships
    entity = relationship("Entity")

    __table_args__ = (
        # Composite unique constraint: same term can't appear twice for same entity/language
        UniqueConstraint('entity_id', 'term', 'language', name='uq_entity_term_language'),
    )
