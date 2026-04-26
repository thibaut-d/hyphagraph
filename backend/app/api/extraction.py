"""
API endpoints for LLM-based knowledge extraction.

Provides endpoints for:
- Entity extraction from text
- Relation extraction from text
- Batch extraction (all-in-one)
"""
import logging

from fastapi import APIRouter, Depends

from app.api.error_handlers import handle_extraction_errors
from app.api.service_dependencies import get_extraction_service
from app.config import settings
from app.dependencies.auth import get_current_user
from app.llm.client import get_llm_provider, is_llm_available
from app.models.user import User
from app.schemas.extraction import (
    BatchExtractionRequest,
    BatchExtractionResponse,
    EntityExtractionRequest,
    EntityExtractionResponse,
    ExtractionStatusResponse,
    RelationExtractionRequest,
    RelationExtractionResponse,
)
from app.services.extraction_service import ExtractionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["extraction"])


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
@handle_extraction_errors
async def extract_entities(
    request: EntityExtractionRequest,
    current_user: User = Depends(get_current_user),
    service: ExtractionService = Depends(get_extraction_service),
) -> EntityExtractionResponse:
    """Extract entities from text."""
    logger.info(f"Entity extraction requested by user {current_user.email}")

    entities = await service.extract_entities(
        text=request.text,
        min_confidence=request.min_confidence
    )

    return EntityExtractionResponse(
        entities=entities,
        count=len(entities),
        text_length=len(request.text)
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
    - associated_with: Non-causal association or co-occurrence
    - prevalence_in: Prevalence/incidence reported within a population or condition
    - mechanism: Biological mechanism underlying effect
    - contraindicated: Should not be used together
    - interacts_with: Drug-drug interaction
    - metabolized_by: Metabolic pathway
    - biomarker_for: Diagnostic/prognostic marker
    - affects_population: Population-specific effect
    - measures: Assessment/tool relation (e.g., VAS measures pain)

    Each relation includes:
    - Relation type
    - Semantic roles array (agent, target, dosage, population, etc.)
    - Confidence level
    - Source text span
    - Optional notes

    Requires authentication.
    """
)
@handle_extraction_errors
async def extract_relations(
    request: RelationExtractionRequest,
    current_user: User = Depends(get_current_user),
    service: ExtractionService = Depends(get_extraction_service),
) -> RelationExtractionResponse:
    """Extract relations from text given a list of entities."""
    logger.info(f"Relation extraction requested by user {current_user.email}")

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


@router.post(
    "/extract/batch",
    response_model=BatchExtractionResponse,
    summary="Extract entities and relations in one request",
    description="""
    Perform batch extraction of entities and source-grounded relations from text.

    More efficient than calling each endpoint separately, as the LLM processes
    the text once and extracts all knowledge types together.

    Returns:
    - Entities: All identified entities
    - Relations: Source-grounded assertions between the entities

    Supports filtering:
    - min_confidence: Filter entities and relations

    Requires authentication.
    """
)
@handle_extraction_errors
async def extract_batch(
    request: BatchExtractionRequest,
    current_user: User = Depends(get_current_user),
    service: ExtractionService = Depends(get_extraction_service),
) -> BatchExtractionResponse:
    """Extract entities and relations in one batch."""
    logger.info(f"Batch extraction requested by user {current_user.email}")

    entities, relations = await service.extract_batch(
        text=request.text,
        min_confidence=request.min_confidence,
    )

    return BatchExtractionResponse(
        entities=entities,
        relations=relations,
        entity_count=len(entities),
        relation_count=len(relations),
        text_length=len(request.text)
    )


@router.get(
    "/extract/status",
    summary="Check extraction service status",
    description="Check if LLM-based extraction service is available and configured.",
    response_model=ExtractionStatusResponse
)
async def extraction_status() -> ExtractionStatusResponse:
    """Check if extraction service is available."""
    available = is_llm_available()
    model_name = None
    if available:
        try:
            model_name = get_llm_provider().get_model_name()
        except RuntimeError:
            pass

    return ExtractionStatusResponse(
        status="ready" if available else "unavailable",
        available=available,
        message="Extraction service is ready" if available else "LLM not configured",
        provider=settings.LLM_PROVIDER if available else None,
        model=model_name,
    )
