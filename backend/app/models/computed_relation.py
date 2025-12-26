from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from uuid import UUID
from app.models.base import Base


class ComputedRelation(Base):
    """
    Represents a computed/inferred relation.

    A computed relation IS a relation, but its source is the "system" source.
    This table stores additional metadata about the computation.
    """
    __tablename__ = "computed_relations"

    # Primary key is the relation_id itself (1:1 with Relation)
    relation_id: Mapped[UUID] = mapped_column(
        ForeignKey("relations.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Deterministic hash of the query scope (for cache lookup)
    scope_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Model version used for computation
    model_version: Mapped[str] = mapped_column(String, nullable=False)

    # Uncertainty measure [0, 1]
    uncertainty: Mapped[float] = mapped_column(Float, nullable=False)

    # When was this computed
    computed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationship to the base relation
    relation = relationship("Relation", foreign_keys=[relation_id])
