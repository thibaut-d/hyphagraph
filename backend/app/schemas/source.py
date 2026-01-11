from uuid import UUID
from typing import Optional, List, Any
from datetime import datetime
from pydantic import field_validator
from app.schemas.base import Schema
from app.llm.schemas import ExtractedEntity, ExtractedRelation


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
    source_metadata: Optional[dict] = None  # doi, pubmed_id, etc.
    created_with_llm: Optional[str] = None

    @field_validator('authors', 'summary', 'source_metadata', mode='before')
    @classmethod
    def convert_null_string_to_none(cls, v: Any) -> Any:
        """Convert string 'null' to None for JSON fields."""
        if v == 'null' or v == 'undefined':
            return None
        return v


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
    source_metadata: Optional[dict] = None
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
    source_metadata: Optional[dict] = None


class SourceWithHistory(SourceRead):
    """Source with full revision history."""
    revisions: List[SourceRevisionRead] = []


# =============================================================================
# Document Upload Schemas
# =============================================================================

class DocumentUploadResponse(Schema):
    """Response schema for document upload endpoint."""
    source_id: UUID
    document_text_preview: str  # First 500 chars
    document_format: str  # pdf, txt, etc.
    character_count: int
    truncated: bool
    warnings: List[str] = []


class EntityLinkMatch(Schema):
    """Match between extracted entity and existing entity."""
    extracted_slug: str
    matched_entity_id: Optional[UUID] = None
    matched_entity_slug: Optional[str] = None
    confidence: float  # 0.0 - 1.0
    match_type: str  # "exact", "synonym", "similar", "none"


class DocumentExtractionPreview(Schema):
    """Preview of extracted entities and relations from document."""
    source_id: UUID
    entities: List[ExtractedEntity]
    relations: List[ExtractedRelation]
    entity_count: int
    relation_count: int
    link_suggestions: List[EntityLinkMatch]


class SaveExtractionRequest(Schema):
    """Request to save user-approved extracted data."""
    source_id: UUID
    entities_to_create: List[ExtractedEntity]  # User-approved entities
    entity_links: dict[str, UUID]  # extracted_slug -> existing_entity_id
    relations_to_create: List[ExtractedRelation]


class SaveExtractionResult(Schema):
    """Result of saving extracted data."""
    entities_created: int
    entities_linked: int
    relations_created: int
    created_entity_ids: List[UUID]
    created_relation_ids: List[UUID]
    warnings: List[str] = []


# Backwards compatibility alias
SourceCreate = SourceWrite