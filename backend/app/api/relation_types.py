from fastapi import APIRouter, Depends

from app.api.service_dependencies import get_relation_type_service
from app.services.relation_type_service import RelationTypeService
from app.dependencies.auth import get_current_active_superuser
from fastapi import status as http_status
from app.schemas.relation_type import (
    RelationTypeCreate,
    RelationTypePromptRead,
    RelationTypeRead,
    RelationTypeStatisticsRead,
    RelationTypeUpdate,
    SuggestNewTypeRequest,
    SuggestNewTypeResponse,
    relation_type_to_read,
)
from app.utils.errors import AppException, ErrorCode, ValidationException


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


@router.get("/{type_id}", response_model=RelationTypeRead)
async def get_relation_type(
    type_id: str,
    service: RelationTypeService = Depends(get_relation_type_service),
    current_user=Depends(get_current_active_superuser),
):
    """Get a single relation type by ID (admin only)."""
    relation_type = await service.get_by_id(type_id)
    if relation_type is None:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Relation type '{type_id}' not found",
        )
    return relation_type_to_read(relation_type)


@router.patch("/{type_id}", response_model=RelationTypeRead)
async def update_relation_type(
    type_id: str,
    payload: RelationTypeUpdate,
    service: RelationTypeService = Depends(get_relation_type_service),
    current_user=Depends(get_current_active_superuser),
):
    """
    Update an existing relation type (admin only).

    Only supplied fields are modified. System types may have their label,
    description, examples, aliases, and category updated, but cannot be
    hard-deleted (use is_active=false to disable instead).
    """
    relation_type = await service.update_relation_type(
        type_id=type_id,
        label=payload.label,
        description=payload.description,
        examples=payload.examples,
        aliases=payload.aliases,
        category=payload.category,
        is_active=payload.is_active,
    )
    if relation_type is None:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Relation type '{type_id}' not found",
        )
    return relation_type_to_read(relation_type)


@router.delete("/{type_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_relation_type(
    type_id: str,
    service: RelationTypeService = Depends(get_relation_type_service),
    current_user=Depends(get_current_active_superuser),
):
    """
    Delete a relation type (admin only).

    System types are soft-deleted (deactivated). User-created types are
    permanently removed.
    """
    deleted = await service.delete_relation_type(type_id)
    if not deleted:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message=f"Relation type '{type_id}' not found",
        )
    return None
