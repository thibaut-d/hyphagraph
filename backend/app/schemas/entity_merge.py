from uuid import UUID

from pydantic import BaseModel


class EntityMergeResult(BaseModel):
    """Result of merging one entity into another."""

    source_slug: str
    target_slug: str
    relations_moved: int
    term_added: bool
    merge_recorded: bool


class AutoMergeAction(BaseModel):
    """Suggested or executed auto-merge action."""

    source_slug: str
    target_slug: str
    similarity: float
    action: str
    result: EntityMergeResult | None = None


class EntityMergeCandidateEntity(BaseModel):
    """Entity summary used when reviewing a possible graph-cleaning merge."""

    id: UUID
    slug: str
    summary: dict[str, str] | None = None


class EntityMergeCandidate(BaseModel):
    """Human-reviewable candidate for merging two entity nodes."""

    source: EntityMergeCandidateEntity
    target: EntityMergeCandidateEntity
    similarity: float
    reason: str
    score_factors: dict[str, float | str | bool] = {}
    proposed_action: str = "merge"
