from uuid import UUID
from typing import Any, Optional
from app.schemas.base import Schema
from app.schemas.relation import RelationRead


class EntityRoleInference(Schema):
    """Inference for a specific (entity, semantic_role) pair."""
    entity_slug: str  # The linked entity
    semantic_role: str  # Semantic role of this entity (agent, target, population, etc.)
    score: Optional[float] = None  # Normalized inference score in [-1, 1]
    coverage: float = 0.0  # Information coverage (number of relations with this entity+role)
    confidence: float = 0.0  # Confidence in [0, 1)
    disagreement: float = 0.0  # Contradiction measure in [0, 1]
    source_count: int = 0  # Number of sources supporting this


class RoleInference(Schema):
    """Computed inference for a specific semantic role."""
    role_type: str  # Semantic role (agent, target, drug, condition, etc.)
    score: Optional[float] = None  # Aggregated score in [-1, 1]
    coverage: float = 0.0  # Information coverage (number of relations)
    confidence: float = 0.0  # Confidence in [0, 1)
    disagreement: float = 0.0  # Contradiction measure in [0, 1]


class InferenceRead(Schema):
    entity_id: UUID
    relations_by_kind: dict[str, list[RelationRead]]
    role_inferences: list[RoleInference] = []  # Computed scores per role