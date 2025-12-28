from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List

from app.database import get_db
from app.schemas.entity import EntityWrite, EntityRead
from app.schemas.filters import EntityFilters
from app.services.entity_service import EntityService
from app.dependencies.auth import get_current_user

router = APIRouter()


@router.post("/", response_model=EntityRead)
async def create_entity(
    payload: EntityWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    service = EntityService(db)
    return await service.create(payload)

@router.get("/", response_model=list[EntityRead])
async def list_entities(
    ui_category_id: Optional[List[str]] = Query(None, description="Filter by UI category"),
    search: Optional[str] = Query(None, description="Search in slug", max_length=100),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List entities with optional filters and pagination.

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
    return await service.list_all(filters=filters)

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