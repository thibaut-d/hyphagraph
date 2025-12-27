from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
import json

from app.database import get_db
from app.schemas.inference import InferenceRead
from app.services.inference_service import InferenceService

router = APIRouter()


@router.get("/entity/{entity_id}", response_model=InferenceRead)
async def infer_entity(
    entity_id: UUID,
    scope: Optional[str] = Query(
        None,
        description='Scope filter as JSON string. Example: {"population": "adults", "condition": "chronic_pain"}',
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute inferences for an entity, optionally filtered by scope.

    Args:
        entity_id: Entity to compute inferences for
        scope: Optional JSON string of scope attributes to filter by.
               Only relations matching ALL specified scope attributes will be included.
               Example: ?scope={"population":"adults"}

    Returns:
        Inference results including grouped relations and computed scores

    Examples:
        GET /inferences/entity/{id}
            → All relations, no filtering

        GET /inferences/entity/{id}?scope={"population":"adults"}
            → Only relations for adults population

        GET /inferences/entity/{id}?scope={"population":"adults","condition":"chronic_pain"}
            → Only relations for adults with chronic pain
    """
    service = InferenceService(db)

    # Parse scope filter if provided
    scope_filter = None
    if scope:
        try:
            scope_filter = json.loads(scope)
            if not isinstance(scope_filter, dict):
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="Scope must be a JSON object")
        except json.JSONDecodeError as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Invalid JSON in scope parameter: {str(e)}")

    return await service.infer_for_entity(entity_id, scope_filter=scope_filter)