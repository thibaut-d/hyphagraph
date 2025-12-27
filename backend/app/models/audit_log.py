"""
Audit log model for tracking security-critical events.

Records authentication events, security actions, and user operations
for security monitoring and compliance.
"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """
    Audit log for security events.

    Tracks important security-related events such as:
    - User logins (successful and failed)
    - Password changes
    - Account modifications
    - Token refreshes
    - Account deletions
    """

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Event information
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of event (e.g., 'login', 'password_change', 'account_deletion')"
    )

    event_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Status of the event ('success' or 'failure')"
    )

    # User information
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who triggered the event (nullable for failed login attempts)"
    )

    user_email: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="Email address used in the event (stored separately in case user is deleted)"
    )

    # Request metadata
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        index=True,
        comment="IP address of the client (supports IPv6)"
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User agent string from the request"
    )

    # Additional details
    details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional event-specific data in JSON format"
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message for failed events"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
