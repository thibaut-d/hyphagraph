"""
API endpoints for LLM-based knowledge extraction.

Provides endpoints for:
- Entity extraction from text
- Relation extraction from text
- Claim extraction from text
- Batch extraction (all-in-one)
"""
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from app.services.extraction_service import ExtractionService
from app.llm.schemas import ExtractedEntity, ExtractedRelation, ExtractedClaim
from app.llm.client import is_llm_available
from app.dependencies.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["extraction"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class TextExtractionRequest(BaseModel):
    """Request schema for text-based extraction."""
    text: str = Field(
        ...,
        description="Text to extract knowledge from",
        min_length=10,
        max_length=50000,  # ~10-15 pages of text
    )
    min_confidence: Literal["high", "medium", "low"] | None = Field(
        None,
        description="Minimum confidence level for results (filters out lower confidence)"
    )


class EntityExtractionRequest(TextExtractionRequest):
    """Request schema for entity extraction."""
    pass


class EntityExtractionResponse(BaseModel):
    """Response schema for entity extraction."""
    entities: list[ExtractedEntity]
    count: int = Field(..., description="Number of entities extracted")
    text_length: int = Field(..., description="Length of input text in characters")


class RelationExtractionRequest(TextExtractionRequest):
    """Request schema for relation extraction."""
    entities: list[dict[str, str]] = Field(
        ...,
        description="List of entities to find relations between (with slug, summary, category)"
    )


class RelationExtractionResponse(BaseModel):
    """Response schema for relation extraction."""
    relations: list[ExtractedRelation]
    count: int = Field(..., description="Number of relations extracted")
    text_length: int = Field(..., description="Length of input text in characters")


class ClaimExtractionRequest(TextExtractionRequest):
    """Request schema for claim extraction."""
    min_evidence_strength: Literal["strong", "moderate", "weak", "anecdotal"] | None = Field(
        None,
        description="Minimum evidence strength for results"
    )


class ClaimExtractionResponse(BaseModel):
    """Response schema for claim extraction."""
    claims: list[ExtractedClaim]
    count: int = Field(..., description="Number of claims extracted")
    text_length: int = Field(..., description="Length of input text in characters")


class BatchExtractionRequest(TextExtractionRequest):
    """Request schema for batch extraction."""
    min_evidence_strength: Literal["strong", "moderate", "weak", "anecdotal"] | None = Field(
        None,
        description="Minimum evidence strength for claims"
    )


class BatchExtractionResponse(BaseModel):
    """Response schema for batch extraction."""
    entities: list[ExtractedEntity]
    relations: list[ExtractedRelation]
    claims: list[ExtractedClaim]
    entity_count: int
    relation_count: int
    claim_count: int
    text_length: int


# =============================================================================
# Dependency: Extraction Service
# =============================================================================

def get_extraction_service() -> ExtractionService:
    """
    Get extraction service instance.

    Raises:
        HTTPException: If LLM is not available
    """
    if not is_llm_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service not available. Please configure OPENAI_API_KEY."
        )
    return ExtractionService()


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/extract/entities",
    response_model=EntityExtractionResponse,
    summary="Extract entities from text",
    description="""
    Extract biomedical entities from text using LLM.

    Extracts:
    - Drugs (medications, pharmaceuticals)
    - Diseases (conditions, disorders)
    - Symptoms (observable signs)
    - Biological mechanisms (pathways, processes)
    - Treatments (therapeutic interventions)
    - Biomarkers (lab values, proteins, genes)
    - Populations (patient groups)
    - Outcomes (clinical endpoints)

    Each entity includes:
    - Unique slug identifier
    - Brief summary description
    - Category classification
    - Confidence level (high, medium, low)
    - Source text span

    Requires authentication.
    """
)
async def extract_entities(
    request: EntityExtractionRequest,
    current_user: User = Depends(get_current_user),
    service: ExtractionService = Depends(get_extraction_service),
) -> EntityExtractionResponse:
    """Extract entities from text."""
    logger.info(f"Entity extraction requested by user {current_user.email}")

    try:
        entities = await service.extract_entities(
            text=request.text,
            min_confidence=request.min_confidence
        )

        return EntityExtractionResponse(
            entities=entities,
            count=len(entities),
            text_length=len(request.text)
        )

    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity extraction failed: {str(e)}"
        )


@router.post(
    "/extract/relations",
    response_model=RelationExtractionResponse,
    summary="Extract relations from text",
    description="""
    Extract relations between entities from text using LLM.

    Relation types:
    - treats: Drug/treatment treats disease/symptom
    - causes: Drug/disease causes symptom/outcome
    - prevents: Drug/treatment prevents disease/outcome
    - increases_risk / decreases_risk: Risk modulation
    - mechanism: Biological mechanism underlying effect
    - contraindicated: Should not be used together
    - interacts_with: Drug-drug interaction
    - metabolized_by: Metabolic pathway
    - biomarker_for: Diagnostic/prognostic marker
    - affects_population: Population-specific effect

    Each relation includes:
    - Subject and object entity slugs
    - Relation type
    - Contextual roles (dosage, route, duration, effect_size, population)
    - Confidence level
    - Source text span
    - Optional notes

    Requires authentication.
    """
)
async def extract_relations(
    request: RelationExtractionRequest,
    current_user: User = Depends(get_current_user),
    service: ExtractionService = Depends(get_extraction_service),
) -> RelationExtractionResponse:
    """Extract relations from text given a list of entities."""
    logger.info(f"Relation extraction requested by user {current_user.email}")

    try:
        relations = await service.extract_relations(
            text=request.text,
            entities=request.entities,
            min_confidence=request.min_confidence
        )

        return RelationExtractionResponse(
            relations=relations,
            count=len(relations),
            text_length=len(request.text)
        )

    except Exception as e:
        logger.error(f"Relation extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Relation extraction failed: {str(e)}"
        )


@router.post(
    "/extract/claims",
    response_model=ClaimExtractionResponse,
    summary="Extract factual claims from text",
    description="""
    Extract factual claims from scientific text using LLM.

    Claim types:
    - efficacy: Treatment effectiveness claims
    - safety: Safety, side effects, risk claims
    - mechanism: Biological mechanism claims
    - epidemiology: Prevalence, risk factor claims
    - other: Other factual claims

    Evidence strength:
    - strong: RCTs, meta-analyses, systematic reviews
    - moderate: Observational studies, case-control studies
    - weak: Case reports, small studies, expert opinion
    - anecdotal: Individual experiences, isolated reports

    Each claim includes:
    - Claim text (the factual statement)
    - Entities involved (referenced entity slugs)
    - Claim type
    - Evidence strength
    - Confidence level
    - Source text span

    Requires authentication.
    """
)
async def extract_claims(
    request: ClaimExtractionRequest,
    current_user: User = Depends(get_current_user),
    service: ExtractionService = Depends(get_extraction_service),
) -> ClaimExtractionResponse:
    """Extract factual claims from text."""
    logger.info(f"Claim extraction requested by user {current_user.email}")

    try:
        claims = await service.extract_claims(
            text=request.text,
            min_evidence_strength=request.min_evidence_strength
        )

        return ClaimExtractionResponse(
            claims=claims,
            count=len(claims),
            text_length=len(request.text)
        )

    except Exception as e:
        logger.error(f"Claim extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Claim extraction failed: {str(e)}"
        )


@router.post(
    "/extract/batch",
    response_model=BatchExtractionResponse,
    summary="Extract entities, relations, and claims in one request",
    description="""
    Perform batch extraction of entities, relations, and claims from text.

    More efficient than calling each endpoint separately, as the LLM processes
    the text once and extracts all knowledge types together.

    Returns:
    - Entities: All identified entities
    - Relations: Relations between the entities
    - Claims: Factual statements with evidence

    Supports filtering:
    - min_confidence: Filter entities and relations
    - min_evidence_strength: Filter claims

    Requires authentication.
    """
)
async def extract_batch(
    request: BatchExtractionRequest,
    current_user: User = Depends(get_current_user),
    service: ExtractionService = Depends(get_extraction_service),
) -> BatchExtractionResponse:
    """Extract entities, relations, and claims in one batch."""
    logger.info(f"Batch extraction requested by user {current_user.email}")

    try:
        entities, relations, claims = await service.extract_batch(
            text=request.text,
            min_confidence=request.min_confidence,
            min_evidence_strength=request.min_evidence_strength
        )

        return BatchExtractionResponse(
            entities=entities,
            relations=relations,
            claims=claims,
            entity_count=len(entities),
            relation_count=len(relations),
            claim_count=len(claims),
            text_length=len(request.text)
        )

    except Exception as e:
        logger.error(f"Batch extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch extraction failed: {str(e)}"
        )


@router.get(
    "/extract/status",
    summary="Check extraction service status",
    description="Check if LLM-based extraction service is available and configured."
)
async def extraction_status() -> dict:
    """Check if extraction service is available."""
    from app.config import settings

    available = is_llm_available()

    return {
        "status": "ready" if available else "unavailable",
        "available": available,
        "message": "Extraction service is ready" if available else "LLM not configured",
        "provider": "OpenAI" if available else None,
        "model": settings.OPENAI_MODEL if available else None
    }
