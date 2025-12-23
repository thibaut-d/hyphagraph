from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ARRAY
from app.models.base import Base, UUIDMixin


class Entity(Base, UUIDMixin):
    __tablename__ = "entities"

    kind: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    ontology_ref: Mapped[str | None] = mapped_column(String)