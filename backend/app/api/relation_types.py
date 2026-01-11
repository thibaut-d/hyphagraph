"""
API endpoints for managing relation types.

Provides:
- List active relation types
- Create new relation type
- Get statistics
- Suggest new type (avoid duplicates)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.relation_type_service import RelationTypeService
from app.dependencies.auth import get_current_user
from app.models.user import User


router = APIRouter(tags=["relation-types"])


# =============================================================================
# Schemas
# =============================================================================

class RelationTypeRead(BaseModel):
    """Read schema for relation type."""
    type_id: str
    label: dict
    description: str
    examples: str | None
    aliases: list[str] | None
    category: str | None
    usage_count: int
    is_system: bool


class RelationTypeCreate(BaseModel):
    """Create schema for relation type."""
    type_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=50)
    label: dict = Field(..., description="i18n labels: {'en': 'Label', 'fr': 'Libellé'}")
    description: str = Field(..., min_length=10, max_length=500)
    examples: str | None = None
    aliases: list[str] | None = None
    category: str | None = Field(None, description="therapeutic, causal, diagnostic, etc.")


class SuggestNewTypeRequest(BaseModel):
    """Request to check if a new relation type should be added."""
    proposed_type: str
    context: str = Field(..., description="Description or use case for this type")


class SuggestNewTypeResponse(BaseModel):
    """Response with suggestion."""
    similar_existing: str | None
    should_add: bool
    reason: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=list[RelationTypeRead])
async def list_relation_types(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all relation types.

    Returns active relation types by default, sorted by usage count.
    Used by:
    - LLM prompt generation (get current vocabulary)
    - UI dropdowns (create/edit relation forms)
    - Analytics (usage statistics)
    """
    service = RelationTypeService(db)
    types = await service.get_all_active()

    return [
        RelationTypeRead(
            type_id=t.type_id,
            label=t.label,
            description=t.description,
            examples=t.examples,
            aliases=eval(t.aliases) if t.aliases else None,
            category=t.category,
            usage_count=t.usage_count,
            is_system=t.is_system
        )
        for t in types
    ]


@router.post("/", response_model=RelationTypeRead)
async def create_relation_type(
    payload: RelationTypeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new relation type.

    Checks for similar existing types before creating to avoid duplicates.
    Only superusers can create new relation types.
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can create relation types"
        )

    service = RelationTypeService(db)

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

        return RelationTypeRead(
            type_id=new_type.type_id,
            label=new_type.label,
            description=new_type.description,
            examples=new_type.examples,
            aliases=eval(new_type.aliases) if new_type.aliases else None,
            category=new_type.category,
            usage_count=new_type.usage_count,
            is_system=new_type.is_system
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/suggest", response_model=SuggestNewTypeResponse)
async def suggest_new_type(
    request: SuggestNewTypeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Check if a new relation type should be added.

    Useful for LLM extraction: when LLM encounters a relationship
    that doesn't fit existing types, check if it's truly new or
    similar to an existing type.
    """
    service = RelationTypeService(db)
    suggestion = await service.suggest_new_type(
        request.proposed_type,
        request.context
    )
    return SuggestNewTypeResponse(**suggestion)


@router.get("/statistics")
async def get_statistics(
    db: AsyncSession = Depends(get_db),
):
    """
    Get relation type usage statistics.

    Returns:
    - Total types
    - System vs user-created types
    - Usage counts
    - Distribution by category
    """
    service = RelationTypeService(db)
    stats = await service.get_statistics()
    return stats


@router.get("/for-llm-prompt")
async def get_for_llm_prompt(
    db: AsyncSession = Depends(get_db),
):
    """
    Get formatted relation type list for LLM prompts.

    Returns a formatted string ready to be inserted into LLM prompts.
    This ensures LLM always uses the current, approved relation types.
    """
    service = RelationTypeService(db)
    prompt_text = await service.get_for_llm_prompt()
    return {"prompt_text": prompt_text}
