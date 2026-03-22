"""
Schemas for the LLM-revision review queue.

Draft revisions (status='draft') are created by bulk_creation_service when
created_with_llm is set. Humans confirm or discard them via this API.
"""
from uuid import UUID
from datetime import datetime
from typing import Literal, Optional
from app.schemas.base import Schema


RevisionKind = Literal["entity", "relation", "source"]


class DraftRevisionRead(Schema):
    """A single draft revision awaiting human confirmation."""
    id: UUID
    revision_kind: RevisionKind
    parent_id: UUID  # entity_id / relation_id / source_id
    created_with_llm: Optional[str] = None
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    # Key human-readable fields (vary by kind; all optional)
    slug: Optional[str] = None          # entity revisions
    kind: Optional[str] = None          # relation / source revisions
    title: Optional[str] = None         # source revisions
    status: str = "draft"


class DraftRevisionListResponse(Schema):
    """Paginated list of draft revisions."""
    items: list[DraftRevisionRead]
    total: int
    page: int
    page_size: int
    has_more: bool


class ConfirmRevisionResponse(Schema):
    """Result of confirming a draft revision."""
    id: UUID
    revision_kind: RevisionKind
    status: str  # "confirmed"


class DiscardRevisionResponse(Schema):
    """Result of discarding (deleting) a draft revision."""
    id: UUID
    revision_kind: RevisionKind
    deleted: bool
