from uuid import UUID
from typing import List, Optional
from datetime import datetime
from app.schemas.base import Schema


class RoleRevisionWrite(Schema):
    """Schema for writing a role within a relation revision."""
    entity_id: UUID
    role_type: str
    weight: Optional[float] = None  # For computed relations
    coverage: Optional[float] = None  # For computed relations


class RoleRevisionRead(RoleRevisionWrite):
    """Schema for reading a role revision."""
    id: UUID
    relation_revision_id: UUID
    entity_slug: Optional[str] = None  # Resolved entity slug for display


class RelationWrite(Schema):
    """
    Schema for creating a new relation.

    Creates both the base Relation and its first RelationRevision.
    """
    source_id: UUID  # Immutable - relation always from one source
    kind: Optional[str] = None
    direction: Optional[str] = None
    confidence: Optional[float] = None
    scope: Optional[dict] = None  # Contextual qualifiers
    notes: Optional[dict] = None  # i18n: {"en": "...", "fr": "..."}
    roles: List[RoleRevisionWrite]
    created_with_llm: Optional[str] = None


class RelationRevisionRead(Schema):
    """Schema for reading a relation revision."""
    id: UUID
    relation_id: UUID
    kind: Optional[str] = None
    direction: Optional[str] = None
    confidence: Optional[float] = None
    scope: Optional[dict] = None
    notes: Optional[dict] = None
    created_with_llm: Optional[str] = None
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    is_current: bool
    roles: List[RoleRevisionRead]


class RelationRead(Schema):
    """
    Schema for reading a relation with its current revision.

    Combines base relation + current revision for convenience.
    """
    id: UUID
    created_at: datetime
    source_id: UUID  # Immutable

    # Current revision data
    kind: Optional[str] = None
    direction: Optional[str] = None
    confidence: Optional[float] = None
    scope: Optional[dict] = None
    notes: Optional[dict] = None
    roles: List[RoleRevisionRead]


class RelationWithHistory(RelationRead):
    """Relation with full revision history."""
    revisions: List[RelationRevisionRead] = []