from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_active_superuser
from app.llm.client import get_llm_provider, is_llm_available
from app.models.user import User
from app.schemas.graph_cleaning import (
    DuplicateRelationCandidate,
    DuplicateRelationApplyRequest,
    GraphCleaningActionResult,
    GraphCleaningAnalysis,
    GraphCleaningCritiqueRequest,
    GraphCleaningCritiqueResponse,
    GraphCleaningDecisionRead,
    GraphCleaningDecisionWrite,
    RoleCorrectionRequest,
    RoleConsistencyCandidate,
)
from app.services.graph_cleaning_service import GraphCleaningService
from app.utils.errors import LLMServiceUnavailableException

router = APIRouter()


@router.get("/analysis", response_model=GraphCleaningAnalysis)
async def get_graph_cleaning_analysis(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """Return read-only graph-cleaning analysis for admin review."""
    return await GraphCleaningService(db).analyze(limit=limit)


@router.get("/duplicate-relations", response_model=list[DuplicateRelationCandidate])
async def list_duplicate_relation_candidates(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """Return possible duplicate relation groups without mutating graph data."""
    return await GraphCleaningService(db).list_duplicate_relation_candidates(limit=limit)


@router.get("/role-consistency", response_model=list[RoleConsistencyCandidate])
async def list_role_consistency_candidates(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """Return role-consistency warnings without mutating graph data."""
    return await GraphCleaningService(db).list_role_consistency_candidates(limit=limit)


@router.get("/decisions", response_model=list[GraphCleaningDecisionRead])
async def list_graph_cleaning_decisions(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """List persisted admin decisions for graph-cleaning candidates."""
    return await GraphCleaningService(db).list_decisions()


@router.post("/decisions", response_model=GraphCleaningDecisionRead)
async def upsert_graph_cleaning_decision(
    payload: GraphCleaningDecisionWrite,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_active_superuser),
):
    """Create or update a graph-cleaning candidate decision."""
    return await GraphCleaningService(db).upsert_decision(payload, admin.id)


@router.post("/critique", response_model=GraphCleaningCritiqueResponse)
async def critique_graph_cleaning_candidates(
    payload: GraphCleaningCritiqueRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_active_superuser),
):
    """Return advisory LLM critique for graph-cleaning candidates."""
    if not is_llm_available():
        raise LLMServiceUnavailableException(
            details="LLM service is not configured. Please set OPENAI_API_KEY."
        )
    return await GraphCleaningService(db).critique_candidates(payload, get_llm_provider())


@router.post("/duplicate-relations/apply", response_model=GraphCleaningActionResult)
async def apply_duplicate_relation_review(
    payload: DuplicateRelationApplyRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_active_superuser),
):
    """Mark duplicate relations after human confirmation."""
    return await GraphCleaningService(db).apply_duplicate_relation_review(payload, admin.id)


@router.post("/relations/{relation_id}/correct-roles", response_model=GraphCleaningActionResult)
async def apply_role_correction(
    relation_id: str,
    payload: RoleCorrectionRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_active_superuser),
):
    """Create a new relation revision with corrected role labels."""
    from uuid import UUID

    return await GraphCleaningService(db).apply_role_correction(
        UUID(relation_id),
        payload,
        admin.id,
    )
