from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel, Json, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.common_types import JsonScalar, ScopeFilter
from app.services.explanation_service import ExplanationService
from app.services.inference_service import InferenceService
from app.services.source_service import SourceService
from app.utils.errors import ValidationException


class InferenceScopeQuery(BaseModel):
    """Typed query contract for optional inference/explanation scope filtering."""

    scope: Annotated[
        Json[dict[str, JsonScalar]] | None,
        Query(
            default=None,
            description=(
                'Scope filter as JSON object. Example: {"population":"adults",'
                ' "condition":"chronic_pain"}'
            ),
        ),
    ] = None

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, value: dict[str, JsonScalar] | None) -> dict[str, JsonScalar] | None:
        if value is None:
            return None

        if not all(isinstance(key, str) for key in value):
            raise ValidationException(
                message="Scope keys must be strings",
                field="scope",
                details="Scope keys must be strings",
            )

        return value

    @property
    def scope_filter(self) -> ScopeFilter | None:
        return self.scope


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
