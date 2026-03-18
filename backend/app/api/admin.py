"""
Admin API endpoints - User management for superusers.

Provides administrative functions for managing users, accessible only
to users with superuser privileges.
"""
from fastapi import APIRouter, Depends, Query
from uuid import UUID

from app.api.service_dependencies import get_admin_service
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.admin import UserListItemRead, UserStatsRead, UserUpdate
from app.services.admin_service import AdminService
from app.utils.errors import ForbiddenException


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
    admin_svc: AdminService = Depends(get_admin_service),
    _admin: User = Depends(require_superuser),
):
    """Get user statistics for admin dashboard."""
    return await admin_svc.get_stats()


@router.get("/users", response_model=list[UserListItemRead])
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_svc: AdminService = Depends(get_admin_service),
    _admin: User = Depends(require_superuser),
):
    """List all users (superuser only)."""
    return await admin_svc.list_users(limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=UserListItemRead)
async def get_user(
    user_id: UUID,
    admin_svc: AdminService = Depends(get_admin_service),
    _admin: User = Depends(require_superuser),
):
    """Get user details by ID (superuser only)."""
    return await admin_svc.get_user(user_id)


@router.put("/users/{user_id}", response_model=UserListItemRead)
async def update_user(
    user_id: UUID,
    updates: UserUpdate,
    admin_svc: AdminService = Depends(get_admin_service),
    admin: User = Depends(require_superuser),
):
    """Update user settings (superuser only)."""
    return await admin_svc.update_user(user_id, updates, admin.id)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    admin_svc: AdminService = Depends(get_admin_service),
    admin: User = Depends(require_superuser),
):
    """Delete user (superuser only)."""
    await admin_svc.delete_user(user_id, admin.id)
    return None
