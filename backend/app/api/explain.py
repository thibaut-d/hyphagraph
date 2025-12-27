"""
Explainability API endpoints.

Provides detailed explanations of computed inferences,
allowing users to trace inference scores back to source documents.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
import json

from app.database import get_db
from app.schemas.explanation import ExplanationRead
from app.services.explanation_service import ExplanationService


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
    db: AsyncSession = Depends(get_db),
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
    service = ExplanationService(db)

    # Parse scope filter (same pattern as inferences.py)
    scope_filter = None
    if scope:
        try:
            scope_filter = json.loads(scope)
            if not isinstance(scope_filter, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Scope must be a JSON object"
                )
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON in scope parameter: {str(e)}"
            )

    try:
        return await service.explain_inference(entity_id, role_type, scope_filter)
    except ValueError as e:
        # Role type not found
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate explanation: {str(e)}"
        )
