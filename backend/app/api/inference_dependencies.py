import json

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common_types import ScopeFilter
from app.services.explanation_service import ExplanationService
from app.services.inference_service import InferenceService
from app.services.source_service import SourceService
from app.utils.errors import ValidationException

def parse_scope_filter(scope: str | None) -> ScopeFilter | None:
    """Parse a JSON scope query parameter into a dict."""
    if not scope:
        return None

    try:
        scope_filter = json.loads(scope)
    except json.JSONDecodeError as error:
        raise ValidationException(
            message="Invalid JSON in scope parameter",
            field="scope",
            details=str(error),
        ) from error

    if not isinstance(scope_filter, dict):
        raise ValidationException(
            message="Scope must be a JSON object",
            field="scope",
            details="Scope must be a JSON object",
        )

    if not all(isinstance(key, str) for key in scope_filter):
        raise ValidationException(
            message="Scope keys must be strings",
            field="scope",
            details="Scope keys must be strings",
        )

    if not all(
        isinstance(value, (str, int, float, bool)) or value is None
        for value in scope_filter.values()
    ):
        raise ValidationException(
            message="Scope values must be JSON scalars",
            field="scope",
            details="Scope values must be strings, numbers, booleans, or null",
        )

    return scope_filter


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
