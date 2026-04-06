"""
Pydantic schemas for knowledge-graph export items.

Used by ExportService to enforce typed serialization for entity,
relation, and source export rows.
"""
from typing import Optional
from pydantic import BaseModel


class RelationRoleExportItem(BaseModel):
    entity_slug: str
    entity_id: str
    role_type: str
    weight: Optional[float] = None
    coverage: Optional[float] = None


class EntityExportItem(BaseModel):
    id: str
    slug: str
    summary_en: Optional[str] = None
    summary_fr: Optional[str] = None
    status: Optional[str] = None
    ui_category_slug: Optional[str] = None
    display_name: Optional[str] = None
    display_name_en: Optional[str] = None
    display_name_fr: Optional[str] = None
    aliases: Optional[str] = None
    ui_category_id: Optional[str] = None  # kept for backward compatibility
    # metadata fields (present when include_metadata=True)
    created_at: Optional[str] = None
    revision_created_at: Optional[str] = None
    created_with_llm: Optional[bool] = None
    created_by_user_id: Optional[str] = None
    llm_review_status: Optional[str] = None


class RelationExportItem(BaseModel):
    id: str
    kind: Optional[str] = None
    direction: Optional[str] = None
    confidence: Optional[float] = None
    status: Optional[str] = None
    source_id: str
    source_title: Optional[str] = None
    roles: list[RelationRoleExportItem] = []
    # metadata fields
    created_at: Optional[str] = None
    revision_created_at: Optional[str] = None
    scope: Optional[dict] = None
    notes: Optional[str] = None
    created_with_llm: Optional[bool] = None
    created_by_user_id: Optional[str] = None
    llm_review_status: Optional[str] = None


class SourceExportItem(BaseModel):
    id: str
    kind: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[list[str]] = None
    year: Optional[int] = None
    origin: Optional[str] = None
    url: Optional[str] = None
    trust_level: Optional[float] = None
    calculated_trust_level: Optional[float] = None
    status: Optional[str] = None
    summary_en: Optional[str] = None
    summary_fr: Optional[str] = None
    # metadata fields
    created_at: Optional[str] = None
    revision_created_at: Optional[str] = None
    created_by_user_id: Optional[str] = None
    created_with_llm: Optional[bool] = None
    llm_review_status: Optional[str] = None
    source_metadata: Optional[dict] = None
