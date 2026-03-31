"""
Pagination response schemas.

Provides generic paginated response format with total count.
Wire shape: { items, total, limit, offset } — the four real fields.
"""

from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response with total count.

    Wire shape: items + total + limit + offset.
    Callers that need derived values (has_more, current_page) should
    compute them from these four fields rather than expecting them on
    the wire.
    """
    items: List[T] = Field(
        ...,
        description="List of items in the current page"
    )

    total: int = Field(
        ...,
        description="Total number of items available (across all pages)",
        ge=0
    )

    limit: int = Field(
        ...,
        description="Maximum number of items per page",
        ge=1
    )

    offset: int = Field(
        ...,
        description="Number of items skipped",
        ge=0
    )
