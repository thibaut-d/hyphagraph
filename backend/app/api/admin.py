"""
Admin API endpoints - User management for superusers.

Provides administrative functions for managing users, accessible only
to users with superuser privileges.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.user_service import UserService


router = APIRouter(tags=["admin"])


# =============================================================================
# Dependencies
# =============================================================================

def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to check if current user is a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return current_user


# =============================================================================
# Schemas
# =============================================================================

class UserUpdate(BaseModel):
    """Schema for updating user from admin panel."""
    is_active: bool | None = None
    is_superuser: bool | None = None
    is_verified: bool | None = None


class UserStats(BaseModel):
    """User statistics for admin dashboard."""
    total_users: int
    active_users: int
    superusers: int
    verified_users: int


class UserListItem(BaseModel):
    """User item for admin list."""
    id: str
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    created_at: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/stats", response_model=UserStats)
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

    return UserStats(
        total_users=total or 0,
        active_users=active or 0,
        superusers=supers or 0,
        verified_users=verified or 0
    )


@router.get("/users", response_model=list[UserListItem])
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


@router.get("/users/{user_id}", response_model=UserListItem)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserListItem(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat() if user.created_at else ""
    )


@router.put("/users/{user_id}", response_model=UserListItem)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-modifications that could lock out
    if user.id == admin.id:
        if updates.is_active == False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate yourself"
            )
        if updates.is_superuser == False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote yourself from superuser"
            )

    # Check if demoting last superuser
    if updates.is_superuser == False and user.is_superuser:
        # Count remaining superusers
        super_count = await db.scalar(
            select(func.count()).select_from(User).where(User.is_superuser == True)
        )
        if super_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote last superuser"
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

    return UserListItem(
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    # Get user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Delete user (CASCADE will delete refresh_tokens, audit_logs)
    await db.delete(user)
    await db.commit()

    return None
