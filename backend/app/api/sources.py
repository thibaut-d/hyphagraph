from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List

from app.database import get_db
from app.schemas.source import SourceWrite, SourceRead
from app.schemas.filters import SourceFilters, SourceFilterOptions
from app.schemas.pagination import PaginatedResponse
from app.services.source_service import SourceService
from app.dependencies.auth import get_current_user

router = APIRouter()

@router.get("/filter-options", response_model=SourceFilterOptions)
async def get_source_filter_options(
    db: AsyncSession = Depends(get_db),
):
    """
    Get available filter options for sources.

    Returns distinct values for filterable fields without fetching full records.
    Useful for populating filter UI controls efficiently.

    Returns:
        - **kinds**: List of distinct source kinds
        - **year_range**: Minimum and maximum publication years [min, max]
    """
    service = SourceService(db)
    return await service.get_filter_options()

@router.post("/", response_model=SourceRead)
async def create_source(
    payload: SourceWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    service = SourceService(db)
    return await service.create(payload)

@router.get("/", response_model=PaginatedResponse[SourceRead])
async def list_sources(
    kind: Optional[List[str]] = Query(None, description="Filter by source kind"),
    year_min: Optional[int] = Query(None, description="Minimum publication year", ge=1000, le=9999),
    year_max: Optional[int] = Query(None, description="Maximum publication year", ge=1000, le=9999),
    trust_level_min: Optional[float] = Query(None, description="Minimum trust level", ge=0.0, le=1.0),
    trust_level_max: Optional[float] = Query(None, description="Maximum trust level", ge=0.0, le=1.0),
    search: Optional[str] = Query(None, description="Search in title, authors, or origin", max_length=100),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List sources with optional filters and pagination.

    Returns paginated results with total count.

    - **kind**: Filter by kind (multiple values use OR logic)
    - **year_min/year_max**: Filter by publication year range
    - **trust_level_min/trust_level_max**: Filter by trust level range
    - **search**: Case-insensitive search in title, authors, or origin
    - **limit**: Maximum number of results to return (default: 50, max: 100)
    - **offset**: Number of results to skip for pagination (default: 0)
    """
    service = SourceService(db)
    filters = SourceFilters(
        kind=kind,
        year_min=year_min,
        year_max=year_max,
        trust_level_min=trust_level_min,
        trust_level_max=trust_level_max,
        search=search,
        limit=limit,
        offset=offset,
    )
    items, total = await service.list_all(filters=filters)
    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )

@router.get("/{source_id}", response_model=SourceRead)
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = SourceService(db)
    return await service.get(source_id)

@router.put("/{source_id}", response_model=SourceRead)
async def update_source(
    source_id: UUID,
    payload: SourceWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    service = SourceService(db)
    return await service.update(source_id, payload, user_id=user.id if user else None)

@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    service = SourceService(db)
    await service.delete(source_id)
    return None