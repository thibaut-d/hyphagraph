from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.schemas.source import SourceWrite, SourceRead
from app.services.source_service import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("/", response_model=SourceRead)
async def create_source(
    payload: SourceWrite,
    db: AsyncSession = Depends(get_db),
):
    service = SourceService(db)
    return await service.create(payload)


@router.get("/{source_id}", response_model=SourceRead)
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = SourceService(db)
    return await service.get(source_id)