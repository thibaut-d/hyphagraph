from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.sql import func
from uuid import UUID
from app.models.base import Base, UUIDMixin


class Relation(Base, UUIDMixin):
    """
    Base relation table - immutable, contains only ID, source reference, and creation timestamp.

    All mutable data lives in RelationRevision.
    This allows full audit trail of all changes to claims.
    """
    __tablename__ = "relations"

    # Source reference (immutable - a relation always comes from one source)
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    source = relationship("Source", back_populates="relations")

    revisions = relationship(
        "RelationRevision",
        back_populates="relation",
        cascade="all, delete-orphan",
        order_by="RelationRevision.created_at.desc()",
    )