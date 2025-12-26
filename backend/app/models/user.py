from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.sql import func
from uuid import UUID
from datetime import datetime
from app.models.base import Base, UUIDMixin


class User(Base, UUIDMixin):
    """
    Minimal user model for authentication.

    Uses custom JWT-based authentication (NOT FastAPI Users).
    Rationale: FastAPI Users is in maintenance mode, we prefer explicit
    authentication logic for security-critical code.
    """
    __tablename__ = "users"

    # Authentication fields
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)

    # Basic permissions
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Email verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_token: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    verification_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Password reset
    reset_token: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )