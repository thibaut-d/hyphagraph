from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from uuid import UUID, uuid4
from datetime import datetime
from app.models.base import Base


class RefreshToken(Base):
    """
    Refresh token model for JWT token rotation.

    Each refresh token is associated with a user and has an expiration time.
    Tokens can be revoked by setting is_revoked to True.
    """
    __tablename__ = "refresh_tokens"

    # Primary key - use token itself as unique identifier
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Token value (hashed for security)
    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    # Expiration timestamp
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Revocation flag
    is_revoked: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
