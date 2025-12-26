from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ARRAY, DateTime
from sqlalchemy.sql import func
from app.models.base import Base, UUIDMixin


class Entity(Base, UUIDMixin):
    """
    Base entity table - immutable, contains only ID and creation timestamp.

    All mutable data lives in EntityRevision.
    This allows full audit trail of all changes.
    """
    __tablename__ = "entities"

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # DEPRECATED FIELDS (kept for backward compatibility during migration)
    # TODO: Remove in future migration after data is migrated to revisions
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    synonyms: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    ontology_ref: Mapped[str | None] = mapped_column(String)

    # Relationships
    revisions = relationship(
        "EntityRevision",
        back_populates="entity",
        cascade="all, delete-orphan",
        order_by="EntityRevision.created_at.desc()",
    )