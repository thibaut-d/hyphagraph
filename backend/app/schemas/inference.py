from uuid import UUID
from typing import Optional
from app.schemas.base import Schema
from app.schemas.relation import RelationRead
from app.schemas.source import SourceRead


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


class EvidenceItemRead(RelationRead):
    source: SourceRead | None = None


class RelationKindSummaryRead(Schema):
    kind: str
    relation_count: int
    average_confidence: float
    supporting_count: int
    contradicting_count: int
    neutral_count: int


class DisagreementGroupRead(Schema):
    kind: str
    supporting: list[EvidenceItemRead]
    contradicting: list[EvidenceItemRead]
    confidence: float


class InferenceStatsRead(Schema):
    total_relations: int
    unique_sources_count: int
    average_confidence: float
    confidence_count: int
    high_confidence_count: int
    low_confidence_count: int
    contradiction_count: int
    relation_type_count: int


class InferenceDetailRead(InferenceRead):
    stats: InferenceStatsRead
    relation_kind_summaries: list[RelationKindSummaryRead]
    evidence_items: list[EvidenceItemRead]
    disagreement_groups: list[DisagreementGroupRead]
