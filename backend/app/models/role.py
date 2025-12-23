from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from app.models.base import Base, UUIDMixin


class Role(Base, UUIDMixin):
    __tablename__ = "roles"

    relation_id: Mapped[str] = mapped_column(
        ForeignKey("relations.id", ondelete="CASCADE"),
        nullable=False,
    )

    entity_id: Mapped[str] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )

    role_type: Mapped[str] = mapped_column(String, nullable=False)

    relation = relationship("Relation", back_populates="roles")