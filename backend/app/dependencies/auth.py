"""
Authentication dependencies for FastAPI endpoints.

Provides get_current_user dependency for protected endpoints.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.utils.auth import decode_access_token


# OAuth2 scheme for token extraction
# tokenUrl points to the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


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
        HTTPException 401: If token is invalid or user not found
        HTTPException 403: If user is inactive
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token to get user_id
    user_id_str = decode_access_token(token)
    if user_id_str is None:
        raise credentials_exception

    # Convert string to UUID
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    # Fetch user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


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
        HTTPException 403: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return current_user
