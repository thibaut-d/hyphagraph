from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float, DateTime
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

    # DEPRECATED FIELDS (kept for backward compatibility during migration)
    # TODO: Remove in future migration after data is migrated to revisions
    kind: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origin: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    trust_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

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