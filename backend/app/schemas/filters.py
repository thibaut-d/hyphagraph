"""
Filter schemas for query parameters.

These schemas define the structure of filter parameters for list endpoints.
"""

from typing import Optional, List
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
