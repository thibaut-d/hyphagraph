from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, ForeignKey
from uuid import UUID
from app.models.base import Base, UUIDMixin


class RelationRoleRevision(Base, UUIDMixin):
    """
    Defines how entities participate in a specific relation revision.

    Roles are tied to relation revisions, not base relations.
    When a relation is revised, all roles are duplicated (snapshot approach).
    """
    __tablename__ = "relation_role_revisions"

    relation_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("relation_revisions.id", ondelete="CASCADE"),
        nullable=False,
    )

    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )

    role_type: Mapped[str] = mapped_column(String, nullable=False)

    # Optional fields for computed relations only
    weight: Mapped[float | None] = mapped_column(Float)  # For computed relations: strength ∈ [-1, 1]
    coverage: Mapped[float | None] = mapped_column(Float)  # For computed relations: information coverage

    # Relationships
    relation_revision = relationship("RelationRevision", back_populates="roles")
