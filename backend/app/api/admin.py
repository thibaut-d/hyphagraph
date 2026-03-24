"""
Admin API endpoints - User management for superusers.

Provides administrative functions for managing users, accessible only
to users with superuser privileges.
"""
from fastapi import APIRouter, Depends, Query
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.service_dependencies import get_admin_service
from app.database import get_db
from app.dependencies.auth import get_current_active_superuser
from app.models.ui_category import UiCategory
from app.models.user import User
from app.schemas.admin import UserListItemRead, UserStatsRead, UserUpdate
from app.schemas.ui_category import UICategoryWrite, UICategoryRead
from app.services.admin_service import AdminService
from app.utils.errors import AppException, ErrorCode


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

def _cat_to_read(cat: UiCategory) -> UICategoryRead:
    return UICategoryRead(
        id=cat.id,
        slug=cat.slug,
        labels=cat.labels,
        description=cat.description,
        order=cat.order,
        created_at=getattr(cat, "created_at", None),
        updated_at=getattr(cat, "updated_at", None),
    )


@router.get("/categories", response_model=list[UICategoryRead])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """List all UI categories (superuser only)."""
    result = await db.execute(select(UiCategory).order_by(UiCategory.order))
    return [_cat_to_read(c) for c in result.scalars().all()]


@router.post("/categories", response_model=UICategoryRead, status_code=201)
async def create_category(
    payload: UICategoryWrite,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """Create a new UI category (superuser only)."""
    cat = UiCategory(
        slug=payload.slug,
        labels=payload.labels,
        description=payload.description,
        order=payload.order,
    )
    db.add(cat)
    try:
        await db.commit()
        await db.refresh(cat)
    except IntegrityError:
        await db.rollback()
        raise AppException(
            status_code=409,
            error_code=ErrorCode.ENTITY_SLUG_CONFLICT,
            message="Category slug already exists",
            field="slug",
            details=f"A UI category with slug '{payload.slug}' already exists.",
        )
    return _cat_to_read(cat)


@router.put("/categories/{category_id}", response_model=UICategoryRead)
async def update_category(
    category_id: UUID,
    payload: UICategoryWrite,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """Update a UI category (superuser only)."""
    result = await db.execute(select(UiCategory).where(UiCategory.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Category not found",
            details=f"No UI category with ID '{category_id}'.",
        )
    cat.slug = payload.slug
    cat.labels = payload.labels
    cat.description = payload.description
    cat.order = payload.order
    try:
        await db.commit()
        await db.refresh(cat)
    except IntegrityError:
        await db.rollback()
        raise AppException(
            status_code=409,
            error_code=ErrorCode.ENTITY_SLUG_CONFLICT,
            message="Category slug already exists",
            field="slug",
            details=f"A UI category with slug '{payload.slug}' already exists.",
        )
    return _cat_to_read(cat)


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """Delete a UI category (superuser only)."""
    result = await db.execute(select(UiCategory).where(UiCategory.id == category_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Category not found",
            details=f"No UI category with ID '{category_id}'.",
        )
    await db.delete(cat)
    await db.commit()
    return None
