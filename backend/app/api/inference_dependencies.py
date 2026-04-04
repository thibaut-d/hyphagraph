import json

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common_types import JsonScalar, ScopeFilter
from app.services.explanation_service import ExplanationService
from app.services.inference_service import InferenceService
from app.services.source_service import SourceService
from app.utils.errors import ValidationException


class InferenceScopeQuery(BaseModel):
    """Typed query contract for optional inference/explanation scope filtering."""

    scope_filter: ScopeFilter | None = None


def get_inference_scope_query(
    scope: str | None = Query(
        default=None,
        description=(
            'Scope filter as JSON object. Example: {"population":"adults",'
            ' "condition":"chronic_pain"}'
        ),
    ),
) -> InferenceScopeQuery:
    if scope is None:
        return InferenceScopeQuery()

    try:
        parsed = json.loads(scope)
    except json.JSONDecodeError as exc:
        raise ValidationException(
            message="Invalid JSON in scope parameter",
            field="scope",
            details=str(exc),
        ) from exc

    if not isinstance(parsed, dict):
        raise ValidationException(
            message="Scope parameter must be a JSON object",
            field="scope",
            details="Provide a JSON object of scope attributes",
        )

    if not all(isinstance(key, str) for key in parsed):
        raise ValidationException(
            message="Scope keys must be strings",
            field="scope",
            details="Scope keys must be strings",
        )

    if not all(isinstance(value, (str, int, float, bool)) or value is None for value in parsed.values()):
        raise ValidationException(
            message="Scope values must be JSON scalars",
            field="scope",
            details="Scope values must be strings, numbers, booleans, or null",
        )

    return InferenceScopeQuery(scope_filter={key: value for key, value in parsed.items()})


def get_inference_service(db: AsyncSession = Depends(get_db)) -> InferenceService:
    """Provide the inference service for API handlers."""
    return InferenceService(db)


def get_source_service(db: AsyncSession = Depends(get_db)) -> SourceService:
    """Provide the source service for API handlers."""
    return SourceService(db)


def get_explanation_service(
    db: AsyncSession = Depends(get_db),
    inference_service: InferenceService = Depends(get_inference_service),
    source_service: SourceService = Depends(get_source_service),
) -> ExplanationService:
    """Provide the explanation service with explicit collaborators."""
    return ExplanationService(
        db=db,
        inference_service=inference_service,
        source_service=source_service,
    )
