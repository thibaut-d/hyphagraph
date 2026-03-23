from fastapi import APIRouter, Depends

from app.api.service_dependencies import get_relation_type_service
from app.services.relation_type_service import RelationTypeService
from app.dependencies.auth import get_current_active_superuser
from app.schemas.relation_type import (
    RelationTypeCreate,
    RelationTypePromptRead,
    RelationTypeRead,
    RelationTypeStatisticsRead,
    SuggestNewTypeRequest,
    SuggestNewTypeResponse,
    relation_type_to_read,
)
from app.utils.errors import ValidationException


router = APIRouter(tags=["relation-types"])


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=list[RelationTypeRead])
async def list_relation_types(
    service: RelationTypeService = Depends(get_relation_type_service),
):
    """
    Get all relation types.

    Returns active relation types by default, sorted by usage count.
    Used by:
    - LLM prompt generation (get current vocabulary)
    - UI dropdowns (create/edit relation forms)
    - Analytics (usage statistics)
    """
    types = await service.get_all_active()

    return [relation_type_to_read(relation_type) for relation_type in types]


@router.post("/", response_model=RelationTypeRead)
async def create_relation_type(
    payload: RelationTypeCreate,
    service: RelationTypeService = Depends(get_relation_type_service),
    current_user=Depends(get_current_active_superuser),
):
    """
    Create a new relation type.

    Checks for similar existing types before creating to avoid duplicates.
    """
    try:
        new_type = await service.create_relation_type(
            type_id=payload.type_id,
            label=payload.label,
            description=payload.description,
            examples=payload.examples,
            aliases=payload.aliases,
            category=payload.category,
            is_system=False
        )

        return relation_type_to_read(new_type)

    except ValueError:
        raise ValidationException(
            message="Invalid relation type data",
            context={"type_id": payload.type_id}
        )


@router.post("/suggest", response_model=SuggestNewTypeResponse)
async def suggest_new_type(
    request: SuggestNewTypeRequest,
    service: RelationTypeService = Depends(get_relation_type_service),
):
    """
    Check if a new relation type should be added.

    Useful for LLM extraction: when LLM encounters a relationship
    that doesn't fit existing types, check if it's truly new or
    similar to an existing type.
    """
    suggestion = await service.suggest_new_type(
        request.proposed_type,
        request.context
    )
    return SuggestNewTypeResponse(**suggestion)


@router.get("/statistics", response_model=RelationTypeStatisticsRead)
async def get_statistics(
    service: RelationTypeService = Depends(get_relation_type_service),
):
    """
    Get relation type usage statistics.

    Returns:
    - Total types
    - System vs user-created types
    - Usage counts
    - Distribution by category
    """
    stats = await service.get_statistics()
    return stats


@router.get("/for-llm-prompt", response_model=RelationTypePromptRead)
async def get_for_llm_prompt(
    service: RelationTypeService = Depends(get_relation_type_service),
):
    """
    Get formatted relation type list for LLM prompts.

    Returns a formatted string ready to be inserted into LLM prompts.
    This ensures LLM always uses the current, approved relation types.
    """
    prompt_text = await service.get_for_llm_prompt()
    return RelationTypePromptRead(prompt_text=prompt_text)
