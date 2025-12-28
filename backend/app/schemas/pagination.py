"""
Pagination response schemas.

Provides generic paginated response format with total count.
"""

from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response with total count.

    Includes the current page of results along with metadata
    about the total number of results available.
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

    @property
    def has_more(self) -> bool:
        """Whether there are more items available."""
        return self.offset + len(self.items) < self.total

    @property
    def current_page(self) -> int:
        """Current page number (1-indexed)."""
        return (self.offset // self.limit) + 1 if self.limit > 0 else 1

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        return (self.total + self.limit - 1) // self.limit if self.limit > 0 else 1
