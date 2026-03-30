"""
Admin API endpoints - User management for superusers.

Provides administrative functions for managing users, accessible only
to users with superuser privileges.
"""
from fastapi import APIRouter, Depends, Query
from uuid import UUID

from app.api.service_dependencies import get_admin_service
from app.dependencies.auth import get_current_active_superuser
from app.models.user import User
from app.schemas.admin import UserListItemRead, UserStatsRead, UserUpdate
from app.schemas.ui_category import UICategoryWrite, UICategoryRead
from app.services.admin_service import AdminService


router = APIRouter(tags=["admin"])


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/stats", response_model=UserStatsRead)
async def get_user_statistics(
    admin_svc: AdminService = Depends(get_admin_service),
    _admin: User = Depends(get_current_active_superuser),
):
    """Get user statistics for admin dashboard."""
    return await admin_svc.get_stats()


@router.get("/users", response_model=list[UserListItemRead])
async def list_users(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_svc: AdminService = Depends(get_admin_service),
    _admin: User = Depends(get_current_active_superuser),
):
    """List all users (superuser only)."""
    return await admin_svc.list_users(limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=UserListItemRead)
async def get_user(
    user_id: UUID,
    admin_svc: AdminService = Depends(get_admin_service),
    _admin: User = Depends(get_current_active_superuser),
):
    """Get user details by ID (superuser only)."""
    return await admin_svc.get_user(user_id)


@router.put("/users/{user_id}", response_model=UserListItemRead)
async def update_user(
    user_id: UUID,
    updates: UserUpdate,
    admin_svc: AdminService = Depends(get_admin_service),
    admin: User = Depends(get_current_active_superuser),
):
    """Update user settings (superuser only)."""
    return await admin_svc.update_user(user_id, updates, admin.id)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    admin_svc: AdminService = Depends(get_admin_service),
    admin: User = Depends(get_current_active_superuser),
):
    """Delete user (superuser only)."""
    await admin_svc.delete_user(user_id, admin.id)
    return None


# =============================================================================
# UI Category management (ADM-02)
# =============================================================================

@router.get("/categories", response_model=list[UICategoryRead])
async def list_categories(
    admin_svc: AdminService = Depends(get_admin_service),
    _admin: User = Depends(get_current_active_superuser),
):
    """List all UI categories (superuser only)."""
    return await admin_svc.list_categories()


@router.post("/categories", response_model=UICategoryRead, status_code=201)
async def create_category(
    payload: UICategoryWrite,
    admin_svc: AdminService = Depends(get_admin_service),
    _admin: User = Depends(get_current_active_superuser),
):
    """Create a new UI category (superuser only)."""
    return await admin_svc.create_category(payload)


@router.put("/categories/{category_id}", response_model=UICategoryRead)
async def update_category(
    category_id: UUID,
    payload: UICategoryWrite,
    admin_svc: AdminService = Depends(get_admin_service),
    _admin: User = Depends(get_current_active_superuser),
):
    """Update a UI category (superuser only)."""
    return await admin_svc.update_category(category_id, payload)


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    admin_svc: AdminService = Depends(get_admin_service),
    _admin: User = Depends(get_current_active_superuser),
):
    """Delete a UI category (superuser only)."""
    await admin_svc.delete_category(category_id)
    return None
