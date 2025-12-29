"""
Search schemas for unified cross-table search functionality.

These schemas define the structure of search requests and responses
for entities, sources, and relations.
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from uuid import UUID


class SearchFilters(BaseModel):
    """
    Query parameters for search across entities, sources, and relations.

    Supports:
    - Full-text search across multiple fields
    - Type filtering (entities, sources, relations, or all)
    - Pagination
    - Optional category/kind filtering
    """
    query: str = Field(
        ...,
        description="Search query (full-text search across relevant fields)",
        min_length=1,
        max_length=200,
        json_schema_extra={"example": "paracetamol efficacy"}
    )

    types: Optional[List[Literal["entity", "source", "relation"]]] = Field(
        None,
        description="Filter by result type. If not provided, searches all types.",
        json_schema_extra={"example": ["entity", "source"]}
    )

    ui_category_id: Optional[List[str]] = Field(
        None,
        description="Filter entities by UI category ID (OR logic)",
        json_schema_extra={"example": ["drug-category-id"]}
    )

    source_kind: Optional[List[str]] = Field(
        None,
        description="Filter sources by kind (OR logic)",
        json_schema_extra={"example": ["study", "article"]}
    )

    limit: int = Field(
        20,
        description="Maximum number of results per type",
        ge=1,
        le=100,
        json_schema_extra={"example": 20}
    )

    offset: int = Field(
        0,
        description="Number of results to skip",
        ge=0,
        json_schema_extra={"example": 0}
    )


class SearchSuggestionRequest(BaseModel):
    """
    Request for search autocomplete suggestions.
    """
    query: str = Field(
        ...,
        description="Partial search query for autocomplete",
        min_length=1,
        max_length=100,
        json_schema_extra={"example": "para"}
    )

    types: Optional[List[Literal["entity", "source"]]] = Field(
        None,
        description="Filter suggestions by type. If not provided, suggests all types.",
        json_schema_extra={"example": ["entity"]}
    )

    limit: int = Field(
        10,
        description="Maximum number of suggestions",
        ge=1,
        le=50,
        json_schema_extra={"example": 10}
    )


class SearchResultBase(BaseModel):
    """
    Base class for search results.
    """
    id: UUID = Field(..., description="Unique identifier")
    type: Literal["entity", "source", "relation"] = Field(..., description="Result type")
    title: str = Field(..., description="Display title/label")
    snippet: Optional[str] = Field(None, description="Text snippet with highlighted matches")
    relevance_score: Optional[float] = Field(None, description="Relevance score (0-1)")


class EntitySearchResult(SearchResultBase):
    """
    Entity search result with entity-specific fields.
    """
    type: Literal["entity"] = "entity"
    slug: str = Field(..., description="Entity slug")
    ui_category_id: Optional[UUID] = Field(None, description="UI category ID")
    summary: Optional[dict] = Field(None, description="i18n summary")


class SourceSearchResult(SearchResultBase):
    """
    Source search result with source-specific fields.
    """
    type: Literal["source"] = "source"
    kind: str = Field(..., description="Source kind (study, article, etc.)")
    year: Optional[int] = Field(None, description="Publication year")
    authors: Optional[List[str]] = Field(None, description="Authors")
    trust_level: Optional[float] = Field(None, description="Trust level (0-1)")


class RelationSearchResult(SearchResultBase):
    """
    Relation search result with relation-specific fields.
    """
    type: Literal["relation"] = "relation"
    kind: Optional[str] = Field(None, description="Relation kind")
    source_id: UUID = Field(..., description="Source ID")
    entity_ids: List[UUID] = Field(..., description="Related entity IDs")
    direction: Optional[str] = Field(None, description="Relation direction (supports, contradicts, etc.)")


# Union type for all search results
SearchResult = EntitySearchResult | SourceSearchResult | RelationSearchResult


class SearchResponse(BaseModel):
    """
    Unified search response containing results of different types.
    """
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="Search results")
    total: int = Field(..., description="Total number of matching results")
    limit: int = Field(..., description="Maximum results requested")
    offset: int = Field(..., description="Offset used for pagination")

    # Per-type counts (useful for filter badges)
    entity_count: int = Field(0, description="Number of entity results")
    source_count: int = Field(0, description="Number of source results")
    relation_count: int = Field(0, description="Number of relation results")


class SearchSuggestion(BaseModel):
    """
    Autocomplete suggestion.
    """
    id: UUID = Field(..., description="Item ID")
    type: Literal["entity", "source"] = Field(..., description="Item type")
    label: str = Field(..., description="Display label")
    secondary: Optional[str] = Field(None, description="Secondary text (kind, year, etc.)")


class SearchSuggestionsResponse(BaseModel):
    """
    Autocomplete suggestions response.
    """
    query: str = Field(..., description="Original query")
    suggestions: List[SearchSuggestion] = Field(..., description="Suggestions")
