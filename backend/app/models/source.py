from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from app.models.base import Base, UUIDMixin


class Source(Base, UUIDMixin):
    """
    Base source table - immutable, contains only ID and creation timestamp.

    All mutable data lives in SourceRevision.
    This allows full audit trail of all changes.
    """
    __tablename__ = "sources"

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    revisions = relationship(
        "SourceRevision",
        back_populates="source",
        cascade="all, delete-orphan",
        order_by="SourceRevision.created_at.desc()",
    )

    relations = relationship(
        "Relation",
        back_populates="source",
        cascade="all, delete-orphan",
    )