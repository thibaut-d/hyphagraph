"""
User management endpoints for administrators.

All endpoints require superuser privileges.
Uses UserService for business logic (matches architectural pattern).
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserRead, UserUpdate
from app.services.user_service import UserService
from app.dependencies.auth import get_current_active_superuser


router = APIRouter(prefix="/users", tags=["User Management"])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency to get UserService instance."""
    return UserService(db)


@router.get("", response_model=list[UserRead])
async def list_users(
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_active_superuser)
):
    """
    List all users (admin only).

    Requires superuser privileges.

    Args:
        user_service: User service instance
        _: Current superuser (for auth check)

    Returns:
        List of all users
    """
    return await user_service.list_all()


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_active_superuser)
):
    """
    Get user by ID (admin only).

    Requires superuser privileges.

    Args:
        user_id: User UUID
        user_service: User service instance
        _: Current superuser (for auth check)

    Returns:
        User information

    Raises:
        HTTPException 404: If user not found
    """
    return await user_service.get(user_id)


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    user_service: UserService = Depends(get_user_service),
    _: User = Depends(get_current_active_superuser)
):
    """
    Update any user (admin only).

    Allows admins to update any user's information including
    email, active status, and password.

    Requires superuser privileges.

    Args:
        user_id: User UUID to update
        payload: Fields to update
        user_service: User service instance
        _: Current superuser (for auth check)

    Returns:
        Updated user information

    Raises:
        HTTPException 404: If user not found
        HTTPException 400: If email already in use
    """
    return await user_service.update(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    user_service: UserService = Depends(get_user_service),
    current_superuser: User = Depends(get_current_active_superuser)
):
    """
    Delete user (admin only).

    Deletes a user and all associated refresh tokens.
    Admins cannot delete themselves for safety.

    Requires superuser privileges.

    Args:
        user_id: User UUID to delete
        user_service: User service instance
        current_superuser: Current superuser (for auth check and safety)

    Returns:
        No content (204)

    Raises:
        HTTPException 404: If user not found
        HTTPException 400: If trying to delete self
    """
    # Prevent admin from deleting themselves
    if user_id == current_superuser.id:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    await user_service.delete(user_id)
    return None
