from fastapi import APIRouter, Depends

from app.api.inference_dependencies import (
    InferenceScopeQuery,
    get_inference_scope_query,
    get_inference_service,
)
from app.api.service_dependencies import get_entity_service
from app.dependencies.auth import get_current_user
from app.llm.client import get_llm_provider, is_llm_available
from app.schemas.inference import (
    EntityAISynthesisRead,
    EntityAISynthesisRequest,
    InferenceDetailRead,
    InferenceRead,
)
from app.services.entity_service import EntityService
from app.services.entity_ai_synthesis_service import EntityAISynthesisService
from app.services.inference_service import InferenceService
from app.utils.errors import LLMServiceUnavailableException

router = APIRouter()


@router.get("/entity/{entity_ref}", response_model=InferenceRead)
async def infer_entity(
    entity_ref: str,
    query: InferenceScopeQuery = Depends(get_inference_scope_query),
    entity_service: EntityService = Depends(get_entity_service),
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
    entity_id = await entity_service.resolve_ref_to_id(entity_ref)
    return await service.infer_for_entity(entity_id, scope_filter=query.scope_filter)


@router.get("/entity/{entity_ref}/detail", response_model=InferenceDetailRead)
async def infer_entity_detail(
    entity_ref: str,
    query: InferenceScopeQuery = Depends(get_inference_scope_query),
    entity_service: EntityService = Depends(get_entity_service),
    service: InferenceService = Depends(get_inference_service),
):
    """Get a screen-oriented inference detail payload for evidence and synthesis views."""
    entity_id = await entity_service.resolve_ref_to_id(entity_ref)
    return await service.get_detail_for_entity(entity_id, scope_filter=query.scope_filter)


@router.post("/entity/{entity_ref}/ai-synthesis", response_model=EntityAISynthesisRead)
async def generate_entity_ai_synthesis(
    entity_ref: str,
    payload: EntityAISynthesisRequest,
    _user=Depends(get_current_user),
    entity_service: EntityService = Depends(get_entity_service),
    service: InferenceService = Depends(get_inference_service),
):
    """
    Generate an on-demand, non-authoritative AI synthesis for an entity.

    This endpoint intentionally performs no work on page load. Callers must
    invoke it explicitly from a user action because it may use a paid LLM API.
    """
    if not is_llm_available():
        raise LLMServiceUnavailableException(
            details="LLM service is not configured. Please set OPENAI_API_KEY."
        )

    entity = await entity_service.get_by_ref(entity_ref)
    inference = await service.get_detail_for_entity(
        entity.id,
        scope_filter=payload.scope_filter,
    )
    synthesis_service = EntityAISynthesisService(llm_provider=get_llm_provider())
    return await synthesis_service.generate(
        entity=entity,
        inference=inference,
        user_language=payload.user_language,
    )
