from uuid import UUID
from typing import Literal, Optional
from datetime import datetime
from pydantic import Field, field_validator
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
    llm_review_status: Optional[str] = None


class EntityRead(Schema):
    """
    Schema for reading an entity with its current revision.

    Combines base entity + current revision for convenience.
    """
    id: UUID
    created_at: datetime
    updated_at: datetime  # created_at of the current revision

    # Current revision data
    slug: str
    summary: Optional[dict[str, str]] = None
    ui_category_id: Optional[UUID] = None
    created_with_llm: Optional[str] = None
    status: str = "confirmed"  # "draft" for LLM-created, "confirmed" for manually entered/reviewed
    llm_review_status: Optional[str] = None

    created_by_user_id: Optional[UUID] = None

    # Computed fields (populated by service on detail views; None in list views)
    consensus_level: Optional[str] = None


class EntityWithHistory(EntityRead):
    """Entity with full revision history."""
    revisions: list[EntityRevisionRead] = []


class EntityPrefillRequest(Schema):
    """Request an AI-assisted, non-authoritative draft for the create-entity form."""
    term: str = Field(..., min_length=1, max_length=200)
    user_language: str = Field("en", pattern=r"^[a-z]{2}$")


class EntityPrefillAlias(Schema):
    """Draft alias term returned by the AI prefill endpoint."""
    term: str = Field(..., min_length=1, max_length=200)
    language: Optional[str] = Field(None, pattern=r"^[a-z]{2}$")
    term_kind: Literal["alias", "abbreviation", "brand"] = "alias"

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip().lower()
        if normalized in {"", "international"}:
            return None
        return normalized

    @field_validator("term_kind", mode="before")
    @classmethod
    def normalize_term_kind(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"abbreviation", "abbr", "acronym", "initialism"}:
            return "abbreviation"
        if normalized in {"brand", "brand_name", "brand-name", "trade", "trade_name", "trademark"}:
            return "brand"
        return "alias"


class EntityPrefillDraft(Schema):
    """Non-authoritative draft values for the create-entity form."""
    slug: str = Field(..., pattern=r"^[a-z][a-z0-9-]*$", min_length=3, max_length=100)
    display_names: dict[str, str] = Field(default_factory=dict)
    summary: dict[str, str] = Field(default_factory=dict)
    aliases: list[EntityPrefillAlias] = Field(default_factory=list)
    ui_category_id: Optional[UUID] = None
