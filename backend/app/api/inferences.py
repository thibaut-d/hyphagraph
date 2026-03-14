from fastapi import APIRouter, Depends, Query
from uuid import UUID
from typing import Optional

from app.api.inference_dependencies import get_inference_service, parse_scope_filter
from app.schemas.inference import InferenceDetailRead, InferenceRead
from app.services.inference_service import InferenceService

router = APIRouter()


@router.get("/entity/{entity_id}", response_model=InferenceRead)
async def infer_entity(
    entity_id: UUID,
    scope: Optional[str] = Query(
        None,
        description='Scope filter as JSON string. Example: {"population": "adults", "condition": "chronic_pain"}',
    ),
    service: InferenceService = Depends(get_inference_service),
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
    scope_filter = parse_scope_filter(scope)
    return await service.infer_for_entity(entity_id, scope_filter=scope_filter)


@router.get("/entity/{entity_id}/detail", response_model=InferenceDetailRead)
async def infer_entity_detail(
    entity_id: UUID,
    scope: Optional[str] = Query(
        None,
        description='Scope filter as JSON string. Example: {"population": "adults", "condition": "chronic_pain"}',
    ),
    service: InferenceService = Depends(get_inference_service),
):
    """Get a screen-oriented inference detail payload for evidence and synthesis views."""
    scope_filter = parse_scope_filter(scope)
    return await service.get_detail_for_entity(entity_id, scope_filter=scope_filter)
