from uuid import UUID
from typing import Any, Optional
from app.schemas.base import Schema
from app.schemas.relation import RelationRead


class RoleInference(Schema):
    """Computed inference for a specific role."""
    role_type: str
    score: Optional[float] = None  # Normalized inference score in [-1, 1]
    coverage: float = 0.0  # Information coverage
    confidence: float = 0.0  # Confidence in [0, 1)
    disagreement: float = 0.0  # Contradiction measure in [0, 1]


class InferenceRead(Schema):
    entity_id: UUID
    relations_by_kind: dict[str, list[RelationRead]]
    role_inferences: list[RoleInference] = []  # Computed scores per role