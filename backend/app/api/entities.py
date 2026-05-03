from fastapi import APIRouter, Depends, Query, Request
from uuid import UUID
from typing import Optional, List

from app.api.service_dependencies import get_entity_service
from app.database import get_db
from app.llm.client import get_prefill_llm_provider, is_llm_available
from app.schemas.entity import (
    EntityPrefillDraft,
    EntityPrefillRequest,
    EntitySmartSuggestRequest,
    EntitySmartSuggestResponse,
    EntityWrite,
    EntityRead,
)
from app.schemas.entity_merge import EntityMergeCandidate, EntityMergeResult
from app.schemas.filters import EntityFilters, EntityFilterOptions
from app.schemas.pagination import PaginatedResponse
from app.services.entity_service import EntityService
from app.services.entity_merge_service import EntityMergeService
from app.services.entity_prefill_service import EntityPrefillService
from app.services.entity_suggest_service import EntitySuggestService
from app.dependencies.auth import get_current_user, get_current_active_superuser
from app.utils.errors import AppException, ErrorCode, LLMServiceUnavailableException
from app.utils.rate_limit import limiter
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/filter-options", response_model=EntityFilterOptions)
async def get_entity_filter_options(
    service: EntityService = Depends(get_entity_service),
):
    """
    Get available filter options for entities.

    Intentionally unauthenticated: returns only aggregated metadata (distinct labels),
    not entity content. No sensitive data is exposed.

    Returns distinct UI categories with i18n labels.
    Useful for populating filter UI controls efficiently.

    Returns:
        - **ui_categories**: List of UI categories with id and i18n labels
        - **consensus_levels**: [Future] Min/max consensus levels from inferences
        - **evidence_quality_range**: [Future] Min/max evidence quality scores
        - **year_range**: [Future] Min/max years from related sources
    """
    return await service.get_filter_options()


@router.post("/", response_model=EntityRead, status_code=201)
async def create_entity(
    payload: EntityWrite,
    service: EntityService = Depends(get_entity_service),
    user=Depends(get_current_user),
):
    return await service.create(payload, user_id=user.id)


@router.post("/prefill", response_model=EntityPrefillDraft)
async def prefill_entity(
    payload: EntityPrefillRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    """
    Build an editable, non-authoritative draft for the create-entity form.

    This endpoint never writes to the database. It requires an authenticated user
    and a configured LLM provider because it may use external AI services.
    """
    if not is_llm_available():
        raise LLMServiceUnavailableException(
            details="LLM service is not configured. Please set OPENAI_API_KEY."
        )
    service = EntityPrefillService(db=db, llm_provider=get_prefill_llm_provider())
    return await service.generate_draft(payload.term, payload.user_language)


@router.post("/smart-suggest", response_model=EntitySmartSuggestResponse)
@limiter.limit("10/minute")
async def smart_suggest_entities(
    request: Request,
    payload: EntitySmartSuggestRequest,
    _user=Depends(get_current_user),
) -> EntitySmartSuggestResponse:
    """
    Suggest entity term names for a free-text topic query.

    Uses an LLM to propose a list of canonical (generic, non-brand) entity names
    relevant to the given topic. The result is non-authoritative and is presented
    to the user for review before any entities are created.

    This endpoint never writes to the database.
    """
    if not is_llm_available():
        raise LLMServiceUnavailableException(
            details="LLM service is not configured. Please set OPENAI_API_KEY."
        )
    service = EntitySuggestService(llm_provider=get_prefill_llm_provider())
    terms = await service.suggest_entity_terms(
        payload.query, payload.count, payload.user_language
    )
    return EntitySmartSuggestResponse(terms=terms, query_used=payload.query)


@router.get("/", response_model=PaginatedResponse[EntityRead])
async def list_entities(
    ui_category_id: Optional[List[str]] = Query(None, description="Filter by UI category"),
    search: Optional[str] = Query(None, description="Search in slug", max_length=100),
    clinical_effects: Optional[List[str]] = Query(None, description="Filter by clinical effects (relation types)"),
    consensus_level: Optional[List[str]] = Query(None, description="Filter by consensus level"),
    evidence_quality_min: Optional[float] = Query(None, description="Minimum evidence quality", ge=0.0, le=1.0),
    evidence_quality_max: Optional[float] = Query(None, description="Maximum evidence quality", ge=0.0, le=1.0),
    recency: Optional[List[str]] = Query(None, description="Filter by recency (recent/older/historical)"),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    service: EntityService = Depends(get_entity_service),
):
    """
    List entities with optional filters and pagination.

    Returns paginated results with total count.

    Basic Filters:
    - **ui_category_id**: Filter by UI category (multiple values use OR logic)
    - **search**: Case-insensitive search in slug

    Advanced Filters (require aggregations):
    - **clinical_effects**: Filter by clinical effects/relation types (treats, causes, etc.)
    - **consensus_level**: Filter by consensus strength (strong, moderate, weak, disputed)
    - **evidence_quality_min/max**: Filter by average trust level of citing sources
    - **recency**: Filter by most recent source year (recent <5y, older 5-10y, historical >10y)

    Pagination:
    - **limit**: Maximum number of results to return (default: 50, max: 100)
    - **offset**: Number of results to skip for pagination (default: 0)
    """
    filters = EntityFilters(
        ui_category_id=ui_category_id,
        search=search,
        clinical_effects=clinical_effects,
        consensus_level=consensus_level,
        evidence_quality_min=evidence_quality_min,
        evidence_quality_max=evidence_quality_max,
        recency=recency,
        limit=limit,
        offset=offset
    )
    items, total = await service.list_all(filters=filters)
    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/merge-candidates", response_model=list[EntityMergeCandidate])
async def list_entity_merge_candidates(
    similarity_threshold: float = Query(
        0.86,
        description="Minimum slug similarity for duplicate-entity candidates",
        ge=0.0,
        le=1.0,
    ),
    limit: int = Query(50, description="Maximum number of candidates", ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_active_superuser),
):
    """
    List possible duplicate entity nodes for graph-cleaning review.

    This endpoint is a dry-run suggestion surface. It does not merge entities and
    LLM or heuristic output must be reviewed by a superuser before mutation.
    """
    merge_service = EntityMergeService(db)
    return await merge_service.list_merge_candidates(
        similarity_threshold=similarity_threshold,
        limit=limit,
    )


@router.get("/{entity_ref}", response_model=EntityRead)
async def get_entity(
    entity_ref: str,
    service: EntityService = Depends(get_entity_service),
):
    return await service.get_by_ref(entity_ref)

@router.put("/{entity_id}", response_model=EntityRead)
async def update_entity(
    entity_id: UUID,
    payload: EntityWrite,
    service: EntityService = Depends(get_entity_service),
    user=Depends(get_current_user),
):
    return await service.update(entity_id, payload, user_id=user.id)

@router.delete("/{entity_id}", status_code=204)
async def delete_entity(
    entity_id: UUID,
    service: EntityService = Depends(get_entity_service),
    user=Depends(get_current_user),
):
    await service.delete(entity_id)
    return None


@router.post("/{entity_id}/merge-into/{target_id}", response_model=EntityMergeResult)
async def merge_entity(
    entity_id: UUID,
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_active_superuser),
):
    """
    Merge source entity into target entity (admin only).

    Moves all current-revision relation roles from source to target,
    adds source slug as a term on the target, and marks the source as merged.
    """
    try:
        merge_service = EntityMergeService(db)
        return await merge_service.merge_entities(
            source_entity_id=entity_id,
            target_entity_id=target_id,
            preserve_source_slug_as_term=True,
            merged_by_user_id=current_user.id,
        )
    except ValueError as exc:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.VALIDATION_ERROR,
            message=str(exc),
        )
