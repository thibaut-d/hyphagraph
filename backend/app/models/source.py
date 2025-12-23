from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Float
from app.models.base import Base, UUIDMixin, TimestampMixin


class Source(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "sources"

    kind: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    origin: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    trust_level: Mapped[float] = mapped_column(Float, nullable=False)

    relations = relationship(
        "Relation",
        back_populates="source",
        cascade="all, delete-orphan",
    )