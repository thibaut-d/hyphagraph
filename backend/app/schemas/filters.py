"""
Filter schemas for query parameters.

These schemas define the structure of filter parameters for list endpoints.
"""

from typing import Optional, List, Tuple
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.
    """
    limit: int = Field(
        50,
        description="Maximum number of results to return",
        ge=1,
        le=100,
        json_schema_extra={"example": 50}
    )

    offset: int = Field(
        0,
        description="Number of results to skip",
        ge=0,
        json_schema_extra={"example": 0}
    )


class EntityFilters(BaseModel):
    """
    Query parameters for filtering entities.

    All parameters are optional. When provided, they filter the results.
    Multiple values in lists are combined with OR logic.
    """
    ui_category_id: Optional[List[str]] = Field(
        None,
        description="Filter by UI category ID. Multiple values allowed (OR logic).",
    )

    search: Optional[str] = Field(
        None,
        description="Search term for slug (case-insensitive)",
        max_length=100
    )

    # Advanced filters (computed/aggregated properties)
    clinical_effects: Optional[List[str]] = Field(
        None,
        description="Filter by clinical effects (relation types). Multiple values allowed (OR logic).",
        json_schema_extra={"example": ["treats", "causes"]}
    )

    consensus_level: Optional[List[str]] = Field(
        None,
        description="Filter by consensus level. Multiple values allowed (OR logic).",
        json_schema_extra={"example": ["strong", "moderate"]}
    )

    evidence_quality_min: Optional[float] = Field(
        None,
        description="Minimum average evidence quality (trust level)",
        ge=0.0,
        le=1.0,
        json_schema_extra={"example": 0.7}
    )

    evidence_quality_max: Optional[float] = Field(
        None,
        description="Maximum average evidence quality (trust level)",
        ge=0.0,
        le=1.0,
        json_schema_extra={"example": 1.0}
    )

    recency: Optional[List[str]] = Field(
        None,
        description="Filter by time relevance. Values: 'recent' (<5 years), 'older' (5-10 years), 'historical' (>10 years)",
        json_schema_extra={"example": ["recent"]}
    )

    limit: int = Field(
        50,
        description="Maximum number of results to return",
        ge=1,
        le=100,
        json_schema_extra={"example": 50}
    )

    offset: int = Field(
        0,
        description="Number of results to skip",
        ge=0,
        json_schema_extra={"example": 0}
    )


class SourceFilters(BaseModel):
    """
    Query parameters for filtering sources.

    All parameters are optional. When provided, they filter the results.
    Multiple values in lists are combined with OR logic.
    """
    kind: Optional[List[str]] = Field(
        None,
        description="Filter by source kind (e.g., 'article', 'book'). Multiple values allowed (OR logic).",
        json_schema_extra={"example": ["article", "study"]}
    )

    year_min: Optional[int] = Field(
        None,
        description="Minimum publication year (inclusive)",
        ge=1000,
        le=9999,
        json_schema_extra={"example": 2020}
    )

    year_max: Optional[int] = Field(
        None,
        description="Maximum publication year (inclusive)",
        ge=1000,
        le=9999,
        json_schema_extra={"example": 2024}
    )

    trust_level_min: Optional[float] = Field(
        None,
        description="Minimum trust level (inclusive)",
        ge=0.0,
        le=1.0,
        json_schema_extra={"example": 0.5}
    )

    trust_level_max: Optional[float] = Field(
        None,
        description="Maximum trust level (inclusive)",
        ge=0.0,
        le=1.0,
        json_schema_extra={"example": 1.0}
    )

    search: Optional[str] = Field(
        None,
        description="Search term for title, authors, or origin (case-insensitive)",
        max_length=100
    )

    # Advanced filters (computed/aggregated properties)
    domain: Optional[List[str]] = Field(
        None,
        description="Filter by medical domain/topic. Multiple values allowed (OR logic).",
        json_schema_extra={"example": ["cardiology", "neurology"]}
    )

    role: Optional[List[str]] = Field(
        None,
        description="Filter by role in graph. Values: 'pillar', 'supporting', 'contradictory', 'single'",
        json_schema_extra={"example": ["pillar", "supporting"]}
    )

    limit: int = Field(
        50,
        description="Maximum number of results to return",
        ge=1,
        le=100,
        json_schema_extra={"example": 50}
    )

    offset: int = Field(
        0,
        description="Number of results to skip",
        ge=0,
        json_schema_extra={"example": 0}
    )


class UICategoryOption(BaseModel):
    """
    UI category option with i18n labels.
    """
    id: str = Field(..., description="UI category ID")
    label: dict = Field(..., description="i18n labels (language code -> label)", json_schema_extra={"example": {"en": "Drug", "fr": "Médicament"}})


class ClinicalEffectOption(BaseModel):
    """
    Clinical effect option with relation type info.
    """
    type_id: str = Field(..., description="Relation type ID")
    label: dict = Field(..., description="i18n labels", json_schema_extra={"example": {"en": "Treats", "fr": "Traite"}})


class EntityFilterOptions(BaseModel):
    """
    Available filter options for entities.

    This provides metadata about what filter values are available,
    useful for populating UI filter controls without fetching all records.
    """
    ui_categories: List[UICategoryOption] = Field(
        ...,
        description="Available UI categories with i18n labels",
        json_schema_extra={"example": [{"id": "drug-id", "label": {"en": "Drug"}}]}
    )

    # Advanced filter options
    clinical_effects: Optional[List[ClinicalEffectOption]] = Field(
        None,
        description="Available clinical effects (relation types)",
        json_schema_extra={"example": [{"type_id": "treats", "label": {"en": "Treats"}}]}
    )

    consensus_levels: List[str] = Field(
        default=["strong", "moderate", "weak", "disputed"],
        description="Available consensus levels",
        json_schema_extra={"example": ["strong", "moderate", "weak", "disputed"]}
    )

    evidence_quality_range: Optional[Tuple[float, float]] = Field(
        None,
        description="Minimum and maximum evidence quality scores [min, max]",
        json_schema_extra={"example": [0.0, 1.0]}
    )

    recency_options: List[str] = Field(
        default=["recent", "older", "historical"],
        description="Available recency categories",
        json_schema_extra={"example": ["recent", "older", "historical"]}
    )

    year_range: Optional[Tuple[int, int]] = Field(
        None,
        description="Minimum and maximum years from related sources [min, max]",
        json_schema_extra={"example": [1995, 2024]}
    )


class SourceFilterOptions(BaseModel):
    """
    Available filter options for sources.

    This provides metadata about what filter values are available,
    useful for populating UI filter controls without fetching all records.
    """
    kinds: List[str] = Field(
        ...,
        description="Available source kinds (distinct values)",
        json_schema_extra={"example": ["article", "book", "website"]}
    )

    year_range: Optional[Tuple[int, int]] = Field(
        None,
        description="Minimum and maximum publication years [min, max]",
        json_schema_extra={"example": [1995, 2024]}
    )

    # Advanced filter options
    domains: Optional[List[str]] = Field(
        None,
        description="Available medical domains/topics",
        json_schema_extra={"example": ["cardiology", "neurology", "general"]}
    )

    roles: List[str] = Field(
        default=["pillar", "supporting", "contradictory", "single"],
        description="Available roles in graph",
        json_schema_extra={"example": ["pillar", "supporting", "contradictory", "single"]}
    )
