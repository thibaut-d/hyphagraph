from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.schemas.entity import EntityWrite, EntityRead
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
    db: AsyncSession = Depends(get_db),
):
    service = EntityService(db)
    return await service.list_all()

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