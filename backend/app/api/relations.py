from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.schemas.relation import RelationWrite, RelationRead
from app.services.relation_service import RelationService
from app.auth.dependencies import current_user

router = APIRouter(prefix="/relations", tags=["relations"])


@router.post("/", response_model=RelationRead)
async def create_relation(
    payload: RelationWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_user),  # 🔒 auth required
):
    service = RelationService(db)
    return await service.create(payload)

@router.get("/by-source/{source_id}", response_model=list[RelationRead])
async def list_relations_by_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RelationService(db)
    return await service.list_by_source(source_id)

@router.get("/{relation_id}", response_model=RelationRead)
async def get_relation(
    relation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = RelationService(db)
    return await service.get(relation_id)