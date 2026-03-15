"""
Admin API endpoints - User management for superusers.

Provides administrative functions for managing users, accessible only
to users with superuser privileges.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.admin import UserListItemRead, UserStatsRead, UserUpdate
from app.services.user_service import UserService
from app.utils.errors import AppException, ErrorCode, ForbiddenException, ValidationException


router = APIRouter(tags=["admin"])


# =============================================================================
# Dependencies
# =============================================================================

def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to check if current user is a superuser."""
    if not current_user.is_superuser:
        raise ForbiddenException(
            message="Superuser privileges required",
            details="You must be a superuser to access this endpoint"
        )
    return current_user


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/stats", response_model=UserStatsRead)
async def get_user_statistics(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superuser),
):
    """
    Get user statistics for admin dashboard.

    Returns counts of total, active, superuser, and verified users.
    """
    # Count total users
    total = await db.scalar(select(func.count()).select_from(User))

    # Count active users
    active = await db.scalar(
        select(func.count()).select_from(User).where(User.is_active == True)
    )

    # Count superusers
    supers = await db.scalar(
        select(func.count()).select_from(User).where(User.is_superuser == True)
    )

    # Count verified users
    verified = await db.scalar(
        select(func.count()).select_from(User).where(User.is_verified == True)
    )

    return UserStatsRead(
        total_users=total or 0,
        active_users=active or 0,
        superusers=supers or 0,
        verified_users=verified or 0
    )


@router.get("/users", response_model=list[UserListItemRead])
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superuser),
):
    """
    List all users (superuser only).

    Returns paginated list of users with their details.
    """
    stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return [
        UserListItem(
            id=str(user.id),
            email=user.email,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_verified=user.is_verified,
            created_at=user.created_at.isoformat() if user.created_at else ""
        )
        for user in users
    ]


@router.get("/users/{user_id}", response_model=UserListItemRead)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_superuser),
):
    """Get user details by ID (superuser only)."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.USER_NOT_FOUND,
            message="User not found",
            details=f"User with ID '{user_id}' does not exist",
            context={"user_id": str(user_id)}
        )

    return UserListItemRead(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat() if user.created_at else ""
    )


@router.put("/users/{user_id}", response_model=UserListItemRead)
async def update_user(
    user_id: UUID,
    updates: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superuser),
):
    """
    Update user settings (superuser only).

    Can modify is_active, is_superuser, is_verified flags.
    """
    # Get user to update
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.USER_NOT_FOUND,
            message="User not found",
            details=f"User with ID '{user_id}' does not exist",
            context={"user_id": str(user_id)}
        )

    # Prevent self-modifications that could lock out
    if user.id == admin.id:
        if updates.is_active == False:
            raise ValidationException(
                message="Cannot deactivate yourself",
                details="You cannot deactivate your own account"
            )
        if updates.is_superuser == False:
            raise ValidationException(
                message="Cannot demote yourself from superuser",
                details="You cannot remove your own superuser privileges"
            )

    # Check if demoting last superuser
    if updates.is_superuser == False and user.is_superuser:
        # Count remaining superusers
        super_count = await db.scalar(
            select(func.count()).select_from(User).where(User.is_superuser == True)
        )
        if super_count <= 1:
            raise ValidationException(
                message="Cannot demote last superuser",
                details="At least one superuser must remain in the system"
            )

    # Apply updates
    if updates.is_active is not None:
        user.is_active = updates.is_active
    if updates.is_superuser is not None:
        user.is_superuser = updates.is_superuser
    if updates.is_verified is not None:
        user.is_verified = updates.is_verified

    await db.commit()
    await db.refresh(user)

    return UserListItemRead(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat() if user.created_at else ""
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superuser),
):
    """
    Delete user (superuser only).

    Cannot delete yourself (prevent lockout).
    """
    # Prevent self-deletion
    if user_id == admin.id:
        raise ValidationException(
            message="Cannot delete yourself",
            details="You cannot delete your own account"
        )

    # Get user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.USER_NOT_FOUND,
            message="User not found",
            details=f"User with ID '{user_id}' does not exist",
            context={"user_id": str(user_id)}
        )

    # Delete user (CASCADE will delete refresh_tokens, audit_logs)
    await db.delete(user)
    await db.commit()

    return None
