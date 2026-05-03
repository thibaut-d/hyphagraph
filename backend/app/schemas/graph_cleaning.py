from uuid import UUID

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class GraphCleaningRelationRole(BaseModel):
    """Role participant summary for graph-cleaning analysis."""

    entity_id: UUID
    entity_slug: str | None = None
    role_type: str


class DuplicateRelationItem(BaseModel):
    """Relation item that belongs to a possible duplicate group."""

    relation_id: UUID
    relation_revision_id: UUID
    source_id: UUID
    source_title: str | None = None
    kind: str | None = None
    direction: str | None = None
    confidence: float | None = None
    roles: list[GraphCleaningRelationRole]


class DuplicateRelationCandidate(BaseModel):
    """Read-only candidate group for possible duplicate relations."""

    fingerprint: str
    reason: str
    relation_count: int
    source_id: UUID
    source_title: str | None = None
    relations: list[DuplicateRelationItem]


class RoleUsageCount(BaseModel):
    """How often one entity appears with a specific role in a relation kind."""

    role_type: str
    count: int
    relation_ids: list[UUID]


class RoleConsistencyCandidate(BaseModel):
    """Read-only role consistency warning for one entity and relation kind."""

    entity_id: UUID
    entity_slug: str | None = None
    relation_kind: str | None = None
    reason: str
    usages: list[RoleUsageCount]


class GraphCleaningAnalysis(BaseModel):
    """Read-only graph-cleaning analysis summary."""

    duplicate_relations: list[DuplicateRelationCandidate]
    role_consistency: list[RoleConsistencyCandidate]


GraphCleaningCandidateType = Literal[
    "entity_merge",
    "duplicate_relation",
    "role_consistency",
]
GraphCleaningDecisionStatus = Literal[
    "open",
    "dismissed",
    "approved",
    "applied",
    "needs_review",
]


class GraphCleaningDecisionWrite(BaseModel):
    """Admin decision for a graph-cleaning candidate."""

    candidate_type: GraphCleaningCandidateType
    candidate_fingerprint: str = Field(..., min_length=1, max_length=128)
    status: GraphCleaningDecisionStatus
    notes: str | None = Field(None, max_length=4000)
    decision_payload: dict | None = None


class GraphCleaningDecisionRead(GraphCleaningDecisionWrite):
    """Persisted graph-cleaning decision."""

    id: UUID
    action_result: dict | None = None
    reviewed_by_user_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


GraphCleaningLLMRecommendation = Literal[
    "recommend",
    "reject",
    "needs_human_review",
]


class GraphCleaningCritiqueRequest(BaseModel):
    """Payload for advisory LLM critique of graph-cleaning candidates."""

    candidates: list[dict] = Field(..., min_length=1, max_length=10)


class GraphCleaningCritiqueItem(BaseModel):
    """One advisory LLM critique item."""

    candidate_fingerprint: str
    recommendation: GraphCleaningLLMRecommendation
    rationale: str
    risks: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)

    @field_validator("risks", "evidence_gaps", mode="before")
    @classmethod
    def normalize_string_list(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        return value


class GraphCleaningCritiqueResponse(BaseModel):
    """Non-authoritative LLM critique response."""

    model: str
    items: list[GraphCleaningCritiqueItem]


class DuplicateRelationApplyRequest(BaseModel):
    """Request to mark duplicate relations after human review."""

    duplicate_relation_ids: list[UUID] = Field(..., min_length=1)
    rationale: str = Field(..., min_length=3, max_length=4000)
    candidate_fingerprint: str | None = Field(None, max_length=128)


class RoleCorrectionItem(BaseModel):
    """One role correction inside a relation revision."""

    entity_id: UUID
    from_role_type: str = Field(..., min_length=1, max_length=64)
    to_role_type: str = Field(..., min_length=1, max_length=64)


class RoleCorrectionRequest(BaseModel):
    """Request to create a new relation revision with corrected role labels."""

    corrections: list[RoleCorrectionItem] = Field(..., min_length=1)
    rationale: str = Field(..., min_length=3, max_length=4000)
    candidate_fingerprint: str | None = Field(None, max_length=128)


class GraphCleaningActionResult(BaseModel):
    """Result of a human-confirmed graph-cleaning action."""

    action: str
    affected_relation_ids: list[UUID]
    created_revision_ids: list[UUID] = Field(default_factory=list)
    status: str
