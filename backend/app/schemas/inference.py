from uuid import UUID
from typing import Optional
from pydantic import Field
from app.schemas.base import Schema
from app.schemas.common_types import ScopeFilter
from app.schemas.relation import RelationRead
from app.schemas.source import SourceRead


class EntityRoleInference(Schema):
    """Inference for a specific (entity, semantic_role) pair."""
    entity_slug: str  # The linked entity
    semantic_role: str  # Semantic role of this entity (agent, target, population, etc.)
    score: Optional[float] = Field(None, ge=-1.0, le=1.0)  # Normalized inference score in [-1, 1]
    coverage: float = 0.0  # Information coverage (number of relations with this entity+role)
    confidence: float = 0.0  # Confidence in [0, 1)
    disagreement: float = 0.0  # Contradiction measure in [0, 1]


class RoleInference(Schema):
    """Computed inference for a specific semantic role."""
    role_type: str  # Semantic role (agent, target, drug, condition, etc.)
    score: Optional[float] = Field(None, ge=-1.0, le=1.0)  # Aggregated score in [-1, 1]
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


class EntityAISynthesisRequest(Schema):
    user_language: str = Field("en", min_length=2, max_length=8)
    scope_filter: ScopeFilter | None = None


class EntityAISynthesisRead(Schema):
    entity_id: UUID
    entity_slug: str
    synthesis: str
    key_points: list[str] = []
    limitations: list[str] = []
    evidence_note: str
    general_knowledge_note: str | None = None
    source_relation_count: int
    source_count: int
    generated_with_llm: str
    token_usage: dict[str, int] = {}
