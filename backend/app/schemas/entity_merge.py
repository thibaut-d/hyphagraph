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
