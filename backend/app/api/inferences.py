from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.schemas.inference import InferenceRead
from app.services.inference_service import InferenceService

router = APIRouter(prefix="/inferences", tags=["inferences"])


@router.get("/entity/{entity_id}", response_model=InferenceRead)
async def infer_entity(
    entity_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = InferenceService(db)
    return await service.infer_for_entity(entity_id)