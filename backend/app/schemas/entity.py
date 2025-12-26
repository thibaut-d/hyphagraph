from uuid import UUID
from typing import Optional, List
from datetime import datetime
from app.schemas.base import Schema


class EntityWrite(Schema):
    """
    Schema for creating a new entity.

    Creates both the base Entity and its first EntityRevision.
    """
    slug: str
    summary: Optional[dict] = None  # i18n: {"en": "...", "fr": "..."}
    ui_category_id: Optional[UUID] = None
    created_with_llm: Optional[str] = None

    # Legacy support (will be deprecated)
    kind: Optional[str] = None
    label: Optional[str] = None
    synonyms: List[str] = []
    ontology_ref: Optional[str] = None


class EntityRevisionRead(Schema):
    """Schema for reading an entity revision."""
    id: UUID
    entity_id: UUID
    slug: str
    summary: Optional[dict] = None
    ui_category_id: Optional[UUID] = None
    created_with_llm: Optional[str] = None
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    is_current: bool


class EntityRead(Schema):
    """
    Schema for reading an entity with its current revision.

    Combines base entity + current revision for convenience.
    """
    id: UUID
    created_at: datetime

    # Current revision data
    slug: str
    summary: Optional[dict] = None
    ui_category_id: Optional[UUID] = None

    # Legacy fields (deprecated, for backward compatibility)
    kind: Optional[str] = None
    label: Optional[str] = None
    synonyms: List[str] = []
    ontology_ref: Optional[str] = None


class EntityWithHistory(EntityRead):
    """Entity with full revision history."""
    revisions: List[EntityRevisionRead] = []