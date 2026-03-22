"""
Explainability API endpoints.

Provides detailed explanations of computed inferences,
allowing users to trace inference scores back to source documents.
"""

import logging

from fastapi import APIRouter, Depends, Query
from uuid import UUID
from typing import Optional

logger = logging.getLogger(__name__)

from app.api.inference_dependencies import get_explanation_service, parse_scope_filter
from app.schemas.explanation import ExplanationRead
from app.services.explanation_service import ExplanationService
from app.utils.errors import AppException, ErrorCode


router = APIRouter()


@router.get("/inference/{entity_id}/{role_type}", response_model=ExplanationRead)
async def explain_inference(
    entity_id: UUID,
    role_type: str,
    scope: Optional[str] = Query(
        None,
        description='Scope filter as JSON string (same format as inference API). '
                    'Example: {"population": "adults", "condition": "chronic_pain"}',
    ),
    service: ExplanationService = Depends(get_explanation_service),
):
    """
    Generate comprehensive explanation for a computed inference.

    Shows:
    - Natural language summary of the inference
    - Source chain (inference → claims → sources)
    - Confidence breakdown (why confidence is X%)
    - Contradiction details (which sources disagree)

    This endpoint enables the ≤2 click traceability requirement:
    1. User views inference on entity detail page
    2. Clicks "Explain" button → this endpoint
    3. Views source chain with clickable source links

    Args:
        entity_id: Entity to explain inference for
        role_type: Role to explain (e.g., "drug", "condition", "effect")
        scope: Optional JSON string of scope filter
               Only relations matching ALL scope attributes will be included.

    Returns:
        Detailed explanation with full provenance chain

    Raises:
        400: Invalid JSON in scope parameter
        404: Role type not found in computed inference
        500: Internal server error during inference computation
    """
    scope_filter = parse_scope_filter(scope)

    try:
        return await service.explain_inference(entity_id, role_type, scope_filter)
    except ValueError:
        # Role type not found
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Role type not found",
            context={"entity_id": str(entity_id), "role_type": role_type}
        )
    except Exception:
        # Unexpected error
        logger.exception("Failed to generate explanation for entity %s role %s", entity_id, role_type)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Failed to generate explanation",
            context={"entity_id": str(entity_id), "role_type": role_type}
        )
