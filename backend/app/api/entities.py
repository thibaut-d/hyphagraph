from fastapi import APIRouter, Depends, Query
from uuid import UUID
from typing import Optional, List

from app.api.service_dependencies import get_entity_service
from app.schemas.entity import EntityWrite, EntityRead
from app.schemas.filters import EntityFilters, EntityFilterOptions
from app.schemas.pagination import PaginatedResponse
from app.services.entity_service import EntityService
from app.dependencies.auth import get_current_user

router = APIRouter()


@router.get("/filter-options", response_model=EntityFilterOptions)
async def get_entity_filter_options(
    service: EntityService = Depends(get_entity_service),
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
    return await service.get_filter_options()


@router.post("/", response_model=EntityRead)
async def create_entity(
    payload: EntityWrite,
    service: EntityService = Depends(get_entity_service),
    user=Depends(get_current_user),
):
    return await service.create(payload, user_id=user.id if user else None)

@router.get("/", response_model=PaginatedResponse[EntityRead])
async def list_entities(
    ui_category_id: Optional[List[str]] = Query(None, description="Filter by UI category"),
    search: Optional[str] = Query(None, description="Search in slug", max_length=100),
    clinical_effects: Optional[List[str]] = Query(None, description="Filter by clinical effects (relation types)"),
    consensus_level: Optional[List[str]] = Query(None, description="Filter by consensus level"),
    evidence_quality_min: Optional[float] = Query(None, description="Minimum evidence quality", ge=0.0, le=1.0),
    evidence_quality_max: Optional[float] = Query(None, description="Maximum evidence quality", ge=0.0, le=1.0),
    recency: Optional[List[str]] = Query(None, description="Filter by recency (recent/older/historical)"),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    service: EntityService = Depends(get_entity_service),
):
    """
    List entities with optional filters and pagination.

    Returns paginated results with total count.

    Basic Filters:
    - **ui_category_id**: Filter by UI category (multiple values use OR logic)
    - **search**: Case-insensitive search in slug

    Advanced Filters (require aggregations):
    - **clinical_effects**: Filter by clinical effects/relation types (treats, causes, etc.)
    - **consensus_level**: Filter by consensus strength (strong, moderate, weak, disputed)
    - **evidence_quality_min/max**: Filter by average trust level of citing sources
    - **recency**: Filter by most recent source year (recent <5y, older 5-10y, historical >10y)

    Pagination:
    - **limit**: Maximum number of results to return (default: 50, max: 100)
    - **offset**: Number of results to skip for pagination (default: 0)
    """
    filters = EntityFilters(
        ui_category_id=ui_category_id,
        search=search,
        clinical_effects=clinical_effects,
        consensus_level=consensus_level,
        evidence_quality_min=evidence_quality_min,
        evidence_quality_max=evidence_quality_max,
        recency=recency,
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
    service: EntityService = Depends(get_entity_service),
):
    return await service.get(entity_id)

@router.put("/{entity_id}", response_model=EntityRead)
async def update_entity(
    entity_id: UUID,
    payload: EntityWrite,
    service: EntityService = Depends(get_entity_service),
    user=Depends(get_current_user),
):
    return await service.update(entity_id, payload, user_id=user.id if user else None)

@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    entity_id: UUID,
    service: EntityService = Depends(get_entity_service),
    user=Depends(get_current_user),
):
    await service.delete(entity_id)
    return None
