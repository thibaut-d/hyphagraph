from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import Field
from app.schemas.base import Schema


class EntityWrite(Schema):
    """
    Schema for creating a new entity.

    Creates both the base Entity and its first EntityRevision.
    """
    slug: str = Field(..., pattern=r"^[a-z][a-z0-9-]*$", min_length=3, max_length=100)
    summary: Optional[dict[str, str]] = None  # i18n: {"en": "...", "fr": "..."}
    ui_category_id: Optional[UUID] = None
    created_with_llm: Optional[str] = None


class EntityRevisionRead(Schema):
    """Schema for reading an entity revision."""
    id: UUID
    entity_id: UUID
    slug: str
    summary: Optional[dict[str, str]] = None
    ui_category_id: Optional[UUID] = None
    created_with_llm: Optional[str] = None
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    is_current: bool
    status: str = "confirmed"


class EntityRead(Schema):
    """
    Schema for reading an entity with its current revision.

    Combines base entity + current revision for convenience.
    """
    id: UUID
    created_at: datetime

    # Current revision data
    slug: str
    summary: Optional[dict[str, str]] = None
    ui_category_id: Optional[UUID] = None
    created_with_llm: Optional[str] = None
    status: str = "confirmed"  # "draft" for LLM-created, "confirmed" for manually entered/reviewed

    # Computed fields (populated by service on detail views; None in list views)
    consensus_level: Optional[str] = None


class EntityWithHistory(EntityRead):
    """Entity with full revision history."""
    revisions: list[EntityRevisionRead] = []
