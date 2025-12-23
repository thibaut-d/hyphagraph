from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, JSON
from app.models.base import Base, UUIDMixin, TimestampMixin


class InferenceCache(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "inference_cache"

    scope_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    uncertainty: Mapped[float | None] = mapped_column(Float)