from uuid import UUID
from typing import Optional, List
from datetime import datetime
from app.schemas.base import Schema


class SourceWrite(Schema):
    """
    Schema for creating a new source.

    Creates both the base Source and its first SourceRevision.
    """
    kind: str
    title: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    origin: Optional[str] = None
    url: str
    trust_level: Optional[float] = None
    summary: Optional[dict] = None  # i18n: {"en": "...", "fr": "..."}
    metadata: Optional[dict] = None  # doi, pubmed_id, etc.
    created_with_llm: Optional[str] = None


class SourceRevisionRead(Schema):
    """Schema for reading a source revision."""
    id: UUID
    source_id: UUID
    kind: str
    title: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    origin: Optional[str] = None
    url: str
    trust_level: Optional[float] = None
    summary: Optional[dict] = None
    metadata: Optional[dict] = None
    created_with_llm: Optional[str] = None
    created_by_user_id: Optional[UUID] = None
    created_at: datetime
    is_current: bool


class SourceRead(Schema):
    """
    Schema for reading a source with its current revision.

    Combines base source + current revision for convenience.
    """
    id: UUID
    created_at: datetime

    # Current revision data
    kind: str
    title: str
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    origin: Optional[str] = None
    url: str
    trust_level: Optional[float] = None
    summary: Optional[dict] = None
    metadata: Optional[dict] = None


class SourceWithHistory(SourceRead):
    """Source with full revision history."""
    revisions: List[SourceRevisionRead] = []


# Backwards compatibility alias
SourceCreate = SourceWrite