from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List

from app.database import get_db
from app.schemas.entity import EntityWrite, EntityRead
from app.schemas.entity_term import EntityTermWrite, EntityTermRead, EntityTermBulkWrite
from app.schemas.filters import EntityFilters, EntityFilterOptions
from app.schemas.pagination import PaginatedResponse
from app.services.entity_service import EntityService
from app.services.entity_term_service import EntityTermService
from app.dependencies.auth import get_current_user

router = APIRouter()


@router.get("/filter-options", response_model=EntityFilterOptions)
async def get_entity_filter_options(
    db: AsyncSession = Depends(get_db),
):
    """
    Get available filter options for entities.

    Returns distinct UI categories with i18n labels.
    Useful for populating filter UI controls efficiently.

    Returns:
        - **ui_categories**: List of UI categories with id and i18n labels
        - **consensus_levels**: [Future] Min/max consensus levels from inferences
        - **evidence_quality_range**: [Future] Min/max evidence quality scores
        - **year_range**: [Future] Min/max years from related sources
    """
    service = EntityService(db)
    return await service.get_filter_options()


@router.post("/", response_model=EntityRead)
async def create_entity(
    payload: EntityWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    service = EntityService(db)
    return await service.create(payload)

@router.get("/", response_model=PaginatedResponse[EntityRead])
async def list_entities(
    ui_category_id: Optional[List[str]] = Query(None, description="Filter by UI category"),
    search: Optional[str] = Query(None, description="Search in slug", max_length=100),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List entities with optional filters and pagination.

    Returns paginated results with total count.

    - **ui_category_id**: Filter by UI category (multiple values use OR logic)
    - **search**: Case-insensitive search in slug
    - **limit**: Maximum number of results to return (default: 50, max: 100)
    - **offset**: Number of results to skip for pagination (default: 0)
    """
    service = EntityService(db)
    filters = EntityFilters(
        ui_category_id=ui_category_id,
        search=search,
        limit=limit,
        offset=offset
    )
    items, total = await service.list_all(filters=filters)
    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )

@router.get("/{entity_id}", response_model=EntityRead)
async def get_entity(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = EntityService(db)
    return await service.get(entity_id)

@router.put("/{entity_id}", response_model=EntityRead)
async def update_entity(
    entity_id: UUID,
    payload: EntityWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    service = EntityService(db)
    return await service.update(entity_id, payload, user_id=user.id if user else None)

@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    service = EntityService(db)
    await service.delete(entity_id)
    return None


# ===== Entity Terms Endpoints =====


@router.get("/{entity_id}/terms", response_model=List[EntityTermRead])
async def list_entity_terms(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all terms/aliases for a specific entity.

    Returns all terms ordered by display_order (nulls last), then by created_at.

    - **entity_id**: The entity UUID
    """
    service = EntityTermService(db)
    return await service.list_by_entity(entity_id)


@router.post("/{entity_id}/terms", response_model=EntityTermRead, status_code=201)
async def create_entity_term(
    entity_id: UUID,
    payload: EntityTermWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Add a new term/alias to an entity.

    Creates a new term for the specified entity. The term must be unique
    within the entity+language combination.

    - **entity_id**: The entity UUID
    - **term**: The term text (required)
    - **language**: ISO 639-1 language code (en, fr) or null for international terms
    - **display_order**: Display priority (lower = shown first)
    """
    service = EntityTermService(db)
    return await service.create(entity_id, payload)


@router.put("/{entity_id}/terms/{term_id}", response_model=EntityTermRead)
async def update_entity_term(
    entity_id: UUID,
    term_id: UUID,
    payload: EntityTermWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Update an existing term.

    - **entity_id**: The entity UUID
    - **term_id**: The term UUID to update
    - **term**: Updated term text
    - **language**: Updated language code
    - **display_order**: Updated display order
    """
    service = EntityTermService(db)
    return await service.update(entity_id, term_id, payload)


@router.delete("/{entity_id}/terms/{term_id}", status_code=204)
async def delete_entity_term(
    entity_id: UUID,
    term_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Delete a term from an entity.

    - **entity_id**: The entity UUID
    - **term_id**: The term UUID to delete
    """
    service = EntityTermService(db)
    await service.delete(entity_id, term_id)
    return None


@router.put("/{entity_id}/terms-bulk", response_model=List[EntityTermRead])
async def bulk_update_entity_terms(
    entity_id: UUID,
    payload: EntityTermBulkWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Replace all terms for an entity.

    Deletes all existing terms and creates new ones from the provided list.
    Useful for entity edit forms where all terms are managed together.

    - **entity_id**: The entity UUID
    - **terms**: List of terms to set (replaces all existing)
    """
    service = EntityTermService(db)
    return await service.bulk_update(entity_id, payload.terms)