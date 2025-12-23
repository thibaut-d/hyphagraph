from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Float, ForeignKey
from app.models.base import Base, UUIDMixin, TimestampMixin


class Relation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "relations"

    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )

    kind: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(String)

    source = relationship("Source", back_populates="relations")
    roles = relationship(
        "Role",
        back_populates="relation",
        cascade="all, delete-orphan",
    )