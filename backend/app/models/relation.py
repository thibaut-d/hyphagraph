from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from uuid import UUID
from app.models.base import Base, UUIDMixin


class Relation(Base, UUIDMixin):
    """
    Base relation table - immutable, contains only ID, source reference, and creation timestamp.

    All mutable data lives in RelationRevision.
    This allows full audit trail of all changes to source-grounded relations.
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
    source = relationship("Source", back_populates="relations", lazy="raise")

    revisions = relationship(
        "RelationRevision",
        back_populates="relation",
        cascade="all, delete-orphan",
        order_by="RelationRevision.created_at.desc()",
        lazy="raise",
        passive_deletes=True,
    )

    # Set to True when a human reviewer rejects the staged extraction that created
    # this relation.  Rejected relations are hidden from listings, search, and export
    # but remain accessible by direct ID for audit purposes.
    is_rejected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    source_extraction = relationship(
        "StagedExtraction",
        foreign_keys="StagedExtraction.materialized_relation_id",
        back_populates="materialized_relation",
        uselist=False,
        lazy="raise",
    )
