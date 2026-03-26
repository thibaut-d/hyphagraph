"""
Authentication dependencies for FastAPI endpoints.

Provides get_current_user dependency for protected endpoints.
"""
from typing import Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.utils.auth import decode_access_token_payload
from app.utils.errors import UnauthorizedException, ForbiddenException


# OAuth2 scheme for token extraction
# tokenUrl points to the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# Same scheme but does not raise 401 when the header is absent
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extract and validate current user from JWT token.

    This dependency:
    1. Extracts the JWT token from Authorization header
    2. Validates and decodes the token
    3. Retrieves the user from database
    4. Checks if user is active

    Args:
        token: JWT access token from Authorization header
        db: Database session

    Returns:
        Current authenticated user

    Raises:
        UnauthorizedException: If token is invalid or user not found
        ForbiddenException: If user is inactive
    """
    # Decode full token payload to extract sub and token version
    payload = decode_access_token_payload(token)
    if payload is None:
        raise UnauthorizedException(
            message="Could not validate credentials",
            details="Invalid or expired token"
        )

    user_id_str: str | None = payload.get("sub")
    token_version: int | None = payload.get("tv")

    if user_id_str is None or token_version is None:
        raise UnauthorizedException(
            message="Could not validate credentials",
            details="Malformed token"
        )

    # Convert string to UUID
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException(
            message="Could not validate credentials",
            details="Invalid user ID format in token"
        )

    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException(
            message="Could not validate credentials",
            details="User not found"
        )

    # Verify token version matches — rejects tokens issued before delete/deactivate
    if user.token_version != token_version:
        raise UnauthorizedException(
            message="Could not validate credentials",
            details="Token has been invalidated"
        )

    # Check if user is active
    if not user.is_active:
        raise ForbiddenException(
            message="Inactive user",
            details="Your account has been deactivated"
        )

    # When verification is required, reject unverified users from protected endpoints.
    if settings.EMAIL_VERIFICATION_REQUIRED and not user.is_verified:
        raise ForbiddenException(
            message="Email not verified",
            details="Please verify your email address before accessing this resource"
        )

    return user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Return the current user if a valid Bearer token is present, or None.

    Never raises — use this for endpoints that accept both authenticated
    and anonymous requests.
    """
    if not token:
        return None
    try:
        return await get_current_user(token=token, db=db)
    except Exception:
        return None


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require current user to be a superuser.

    This dependency builds on get_current_user and additionally
    checks that the user has superuser privileges.

    Args:
        current_user: Current authenticated user (from get_current_user)

    Returns:
        Current authenticated superuser

    Raises:
        ForbiddenException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise ForbiddenException(
            message="Superuser privileges required",
            details="This action requires administrator privileges"
        )
    return current_user
