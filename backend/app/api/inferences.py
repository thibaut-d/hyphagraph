from fastapi import APIRouter, Depends
from uuid import UUID

from app.api.inference_dependencies import InferenceScopeQuery, get_inference_service
from app.schemas.inference import InferenceDetailRead, InferenceRead
from app.services.inference_service import InferenceService

router = APIRouter()


@router.get("/entity/{entity_id}", response_model=InferenceRead)
async def infer_entity(
    entity_id: UUID,
    query: InferenceScopeQuery = Depends(),
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
    return await service.infer_for_entity(entity_id, scope_filter=query.scope_filter)


@router.get("/entity/{entity_id}/detail", response_model=InferenceDetailRead)
async def infer_entity_detail(
    entity_id: UUID,
    query: InferenceScopeQuery = Depends(),
    service: InferenceService = Depends(get_inference_service),
):
    """Get a screen-oriented inference detail payload for evidence and synthesis views."""
    return await service.get_detail_for_entity(entity_id, scope_filter=query.scope_filter)
