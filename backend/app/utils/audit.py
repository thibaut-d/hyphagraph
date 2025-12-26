"""
Audit logging utilities for tracking security events.

Provides functions to log authentication events, password changes,
and other security-critical operations.
"""
import logging
from typing import Any
from uuid import UUID
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str | None:
    """
    Extract client IP address from request.

    Checks X-Forwarded-For header first (for proxied requests),
    then falls back to direct client IP.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address or None
    """
    # Check for X-Forwarded-For header (common in reverse proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        return forwarded_for.split(",")[0].strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return None


def get_user_agent(request: Request) -> str | None:
    """
    Extract user agent from request.

    Args:
        request: FastAPI request object

    Returns:
        User agent string or None
    """
    return request.headers.get("User-Agent")


async def log_audit_event(
    db: AsyncSession,
    event_type: str,
    event_status: str,
    user_id: UUID | None = None,
    user_email: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    """
    Log an audit event to the database.

    This function creates an audit log entry with the provided information.
    If an error occurs during logging, it logs the error but does not raise
    an exception (to avoid breaking the application flow).

    Args:
        db: Database session
        event_type: Type of event (e.g., 'login', 'password_change')
        event_status: Status of the event ('success' or 'failure')
        user_id: User ID (optional, may be None for failed login attempts)
        user_email: Email address used in the event
        ip_address: Client IP address
        user_agent: User agent string
        details: Additional event-specific data
        error_message: Error message for failed events
    """
    try:
        audit_log = AuditLog(
            event_type=event_type,
            event_status=event_status,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            error_message=error_message,
        )

        db.add(audit_log)
        await db.commit()

    except Exception as e:
        # Log the error but don't raise - we don't want audit logging
        # failures to break the application
        logger.error(f"Failed to log audit event: {e}")
        await db.rollback()


async def log_login_attempt(
    db: AsyncSession,
    request: Request,
    email: str,
    success: bool,
    user_id: UUID | None = None,
    error_message: str | None = None,
) -> None:
    """
    Log a login attempt (successful or failed).

    Args:
        db: Database session
        request: FastAPI request object
        email: Email address used in login attempt
        success: Whether login was successful
        user_id: User ID (only if login succeeded)
        error_message: Error message (only if login failed)
    """
    await log_audit_event(
        db=db,
        event_type="login",
        event_status="success" if success else "failure",
        user_id=user_id,
        user_email=email,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        error_message=error_message,
    )


async def log_password_change(
    db: AsyncSession,
    request: Request,
    user_id: UUID,
    user_email: str,
    success: bool,
    error_message: str | None = None,
) -> None:
    """
    Log a password change attempt.

    Args:
        db: Database session
        request: FastAPI request object
        user_id: User ID
        user_email: User email address
        success: Whether password change was successful
        error_message: Error message (only if failed)
    """
    await log_audit_event(
        db=db,
        event_type="password_change",
        event_status="success" if success else "failure",
        user_id=user_id,
        user_email=user_email,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        error_message=error_message,
    )


async def log_account_deletion(
    db: AsyncSession,
    request: Request,
    user_id: UUID,
    user_email: str,
) -> None:
    """
    Log an account deletion.

    Args:
        db: Database session
        request: FastAPI request object
        user_id: User ID
        user_email: User email address
    """
    await log_audit_event(
        db=db,
        event_type="account_deletion",
        event_status="success",
        user_id=user_id,
        user_email=user_email,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


async def log_token_refresh(
    db: AsyncSession,
    request: Request,
    user_id: UUID,
    user_email: str,
    success: bool,
    error_message: str | None = None,
) -> None:
    """
    Log a token refresh attempt.

    Args:
        db: Database session
        request: FastAPI request object
        user_id: User ID
        user_email: User email address
        success: Whether token refresh was successful
        error_message: Error message (only if failed)
    """
    await log_audit_event(
        db=db,
        event_type="token_refresh",
        event_status="success" if success else "failure",
        user_id=user_id,
        user_email=user_email,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        error_message=error_message,
    )


async def log_registration(
    db: AsyncSession,
    request: Request,
    email: str,
    success: bool,
    user_id: UUID | None = None,
    error_message: str | None = None,
) -> None:
    """
    Log a user registration attempt.

    Args:
        db: Database session
        request: FastAPI request object
        email: Email address used in registration
        success: Whether registration was successful
        user_id: User ID (only if registration succeeded)
        error_message: Error message (only if failed)
    """
    await log_audit_event(
        db=db,
        event_type="registration",
        event_status="success" if success else "failure",
        user_id=user_id,
        user_email=email,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        error_message=error_message,
    )
