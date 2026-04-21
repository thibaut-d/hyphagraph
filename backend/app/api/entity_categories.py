"""
API endpoints for entity category management.

Admin-only CRUD for the entity category controlled vocabulary.
"""
from fastapi import APIRouter, Depends
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_active_superuser
from app.schemas.entity_category import (
    EntityCategoryCreate,
    EntityCategoryRead,
    EntityCategoryUpdate,
    entity_category_to_read,
)
from app.services.entity_category_service import EntityCategoryService
from app.utils.errors import AppException, ErrorCode, ValidationException


class EntityCategoryMergeResult(BaseModel):
    updated_staged: int
    deactivated_category: str

router = APIRouter(tags=["entity-categories"])


def get_entity_category_service(db: AsyncSession = Depends(get_db)) -> EntityCategoryService:
    return EntityCategoryService(db)


@router.get("/", response_model=list[EntityCategoryRead])
async def list_entity_categories(
    service: EntityCategoryService = Depends(get_entity_category_service),
):
    """List all active entity categories (public — used by dropdowns)."""
    return [entity_category_to_read(r) for r in await service.get_all_active()]


@router.get("/all", response_model=list[EntityCategoryRead])
async def list_all_entity_categories(
    service: EntityCategoryService = Depends(get_entity_category_service),
    current_user=Depends(get_current_active_superuser),
):
    """List all entity categories including inactive ones (admin only)."""
    return [entity_category_to_read(r) for r in await service.get_all()]


@router.post("/", response_model=EntityCategoryRead)
async def create_entity_category(
    payload: EntityCategoryCreate,
    service: EntityCategoryService = Depends(get_entity_category_service),
    current_user=Depends(get_current_active_superuser),
):
    """Create a new entity category (admin only)."""
    try:
        row = await service.create(
            category_id=payload.category_id,
            label=payload.label,
            description=payload.description,
            examples=payload.examples,
        )
        return entity_category_to_read(row)
    except ValueError:
        raise ValidationException(
            message="Entity category already exists or invalid data",
            context={"category_id": payload.category_id},
        )


@router.get("/{category_id}", response_model=EntityCategoryRead)
async def get_entity_category(
    category_id: str,
    service: EntityCategoryService = Depends(get_entity_category_service),
    current_user=Depends(get_current_active_superuser),
):
    """Get a single entity category by ID (admin only)."""
    row = await service.get_by_id(category_id)
    if row is None:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Entity category '{category_id}' not found",
        )
    return entity_category_to_read(row)


@router.patch("/{category_id}", response_model=EntityCategoryRead)
async def update_entity_category(
    category_id: str,
    payload: EntityCategoryUpdate,
    service: EntityCategoryService = Depends(get_entity_category_service),
    current_user=Depends(get_current_active_superuser),
):
    """Update an entity category (admin only). Only supplied fields are modified."""
    row = await service.update(
        category_id=category_id,
        label=payload.label,
        description=payload.description,
        examples=payload.examples,
        is_active=payload.is_active,
    )
    if row is None:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Entity category '{category_id}' not found",
        )
    return entity_category_to_read(row)


@router.get("/{category_id}/merge-preview", response_model=dict)
async def preview_entity_category_merge(
    category_id: str,
    service: EntityCategoryService = Depends(get_entity_category_service),
    current_user=Depends(get_current_active_superuser),
):
    """
    Return counts of items that would be affected by merging this category (admin only).

    Response: { pending_staged: int }
    """
    row = await service.get_by_id(category_id)
    if row is None:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Entity category '{category_id}' not found",
        )
    pending_staged = await service.count_pending_staged_by_category(category_id)
    return {"pending_staged": pending_staged}


@router.post(
    "/{category_id}/merge-into/{target_id}",
    response_model=EntityCategoryMergeResult,
)
async def merge_entity_category(
    category_id: str,
    target_id: str,
    service: EntityCategoryService = Depends(get_entity_category_service),
    current_user=Depends(get_current_active_superuser),
):
    """
    Merge source category into target category (admin only).

    Re-labels all pending staged entity extractions from source to target,
    then soft-deletes the source category.
    """
    try:
        result = await service.merge_entity_categories(
            source_id=category_id,
            target_id=target_id,
        )
        return EntityCategoryMergeResult(**result)
    except ValueError as exc:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.VALIDATION_ERROR,
            message=str(exc),
        )


@router.delete("/{category_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_entity_category(
    category_id: str,
    service: EntityCategoryService = Depends(get_entity_category_service),
    current_user=Depends(get_current_active_superuser),
):
    """
    Delete an entity category (admin only).

    System categories are soft-deleted (deactivated). User-created categories
    are permanently removed.
    """
    deleted = await service.delete(category_id)
    if not deleted:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Entity category '{category_id}' not found",
        )
    return None
