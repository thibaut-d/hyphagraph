from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.schemas.entity import EntityWrite, EntityRead
from app.services.entity_service import EntityService
from app.auth.dependencies import current_user

router = APIRouter(prefix="/entities", tags=["entities"])


@router.post("/", response_model=EntityRead)
async def create_entity(
    payload: EntityWrite,
    db: AsyncSession = Depends(get_db),
):
    service = EntityService(db)
    return await service.create(payload)


@router.get("/{entity_id}", response_model=EntityRead)
async def get_entity(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = EntityService(db)
    return await service.get(entity_id)