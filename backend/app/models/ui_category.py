from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON, Integer, DateTime
from sqlalchemy.sql import func
from app.models.base import Base, UUIDMixin


class UiCategory(Base, UUIDMixin):
    """
    UI Categories for display and navigation.

    These are NOT semantic categories - they're purely for UX purposes.
    Examples: "Drugs", "Diseases", "Biological Mechanisms", "Effects"
    """
    __tablename__ = "ui_categories"

    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    labels: Mapped[dict] = mapped_column(JSON, nullable=False)  # i18n: {"en": "Drugs", "fr": "Médicaments"}
    description: Mapped[dict | None] = mapped_column(JSON)  # i18n descriptions
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )
