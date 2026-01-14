from uuid import UUID
from typing import Any, Optional
from app.schemas.base import Schema
from app.schemas.relation import RelationRead


class RoleInference(Schema):
    """Computed inference for a specific relation type."""
    role_type: str  # Actually the relation type (treats, biomarker_for, etc.)
    score: Optional[float] = None  # Normalized inference score in [-1, 1]
    coverage: float = 0.0  # Information coverage (number of relations)
    confidence: float = 0.0  # Confidence in [0, 1)
    disagreement: float = 0.0  # Contradiction measure in [0, 1]
    connected_entities: list[str] = []  # List of entity slugs connected via this relation type


class InferenceRead(Schema):
    entity_id: UUID
    relations_by_kind: dict[str, list[RelationRead]]
    role_inferences: list[RoleInference] = []  # Computed scores per role