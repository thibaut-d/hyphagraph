from uuid import UUID
from typing import Optional
from datetime import datetime
from app.schemas.base import Schema


class EntityTermWrite(Schema):
    """
    Schema for creating or updating an entity term.

    Entity terms allow entities to have multiple names/aliases
    in different languages or contexts.
    """
    term: str
    language: Optional[str] = None  # ISO 639-1 code (en, fr) or None for international
    display_order: Optional[int] = None  # Lower = shown first


class EntityTermRead(Schema):
    """Schema for reading an entity term."""
    id: UUID
    entity_id: UUID
    term: str
    language: Optional[str] = None
    display_order: Optional[int] = None
    created_at: datetime


class EntityTermBulkWrite(Schema):
    """
    Schema for bulk updating all terms for an entity.

    Replaces all existing terms with the provided list.
    Useful for entity edit forms where all terms are managed together.
    """
    terms: list[EntityTermWrite]
