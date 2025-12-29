"""
Search API endpoints for unified cross-table search.

Provides:
- POST /search - Unified search across entities, sources, and relations
- POST /search/suggestions - Autocomplete suggestions for typeahead
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Literal

from app.database import get_db
from app.schemas.search import (
    SearchFilters,
    SearchResponse,
    SearchSuggestionRequest,
    SearchSuggestionsResponse,
)
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResponse)
async def search(
    query: str = Query(
        ...,
        description="Search query (full-text search across entities, sources, relations)",
        min_length=1,
        max_length=200,
    ),
    types: Optional[List[Literal["entity", "source", "relation"]]] = Query(
        None,
        description="Filter by result type (entity, source, relation). If not provided, searches all types.",
    ),
    ui_category_id: Optional[List[str]] = Query(
        None,
        description="Filter entities by UI category ID (OR logic)",
    ),
    source_kind: Optional[List[str]] = Query(
        None,
        description="Filter sources by kind (OR logic)",
    ),
    limit: int = Query(
        20,
        description="Maximum number of results",
        ge=1,
        le=100,
    ),
    offset: int = Query(
        0,
        description="Number of results to skip for pagination",
        ge=0,
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Unified search across entities, sources, and relations.

    Performs full-text search with relevance ranking across:
    - **Entities**: slug, summary, terms/aliases
    - **Sources**: title, authors, origin
    - **Relations**: kind, notes

    Returns ranked results with snippets and relevance scores.

    **Parameters:**
    - **query**: Search query (required, 1-200 characters)
    - **types**: Filter by result type (optional, defaults to all types)
    - **ui_category_id**: Filter entities by UI category (optional, OR logic)
    - **source_kind**: Filter sources by kind (optional, OR logic)
    - **limit**: Maximum results per type (default: 20, max: 100)
    - **offset**: Pagination offset (default: 0)

    **Returns:**
    - Unified list of search results sorted by relevance
    - Total count per type (entity_count, source_count, relation_count)
    - Total overall count

    **Example:**
    ```
    POST /api/search?query=paracetamol&types=entity&types=source&limit=10
    ```
    """
    service = SearchService(db)

    filters = SearchFilters(
        query=query,
        types=types,
        ui_category_id=ui_category_id,
        source_kind=source_kind,
        limit=limit,
        offset=offset,
    )

    (
        results,
        total,
        entity_count,
        source_count,
        relation_count,
    ) = await service.search(filters)

    return SearchResponse(
        query=query,
        results=results,
        total=total,
        limit=limit,
        offset=offset,
        entity_count=entity_count,
        source_count=source_count,
        relation_count=relation_count,
    )


@router.post("/suggestions", response_model=SearchSuggestionsResponse)
async def get_suggestions(
    query: str = Query(
        ...,
        description="Partial search query for autocomplete",
        min_length=1,
        max_length=100,
    ),
    types: Optional[List[Literal["entity", "source"]]] = Query(
        None,
        description="Filter suggestions by type (entity, source). If not provided, suggests all types.",
    ),
    limit: int = Query(
        10,
        description="Maximum number of suggestions",
        ge=1,
        le=50,
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get autocomplete suggestions for search queries.

    Provides fast typeahead suggestions based on prefix matching:
    - **Entities**: Matches entity slugs starting with the query
    - **Sources**: Matches source titles starting with the query

    Suggestions are ordered by:
    - Entities: Alphabetically by slug
    - Sources: By year (descending), then title

    **Parameters:**
    - **query**: Partial search query (required, 1-100 characters)
    - **types**: Filter suggestions by type (optional, defaults to both entities and sources)
    - **limit**: Maximum number of suggestions (default: 10, max: 50)

    **Returns:**
    - List of suggestions with ID, type, label, and optional secondary text
    - Original query for reference

    **Example:**
    ```
    POST /api/search/suggestions?query=para&limit=5
    ```

    **Response:**
    ```json
    {
      "query": "para",
      "suggestions": [
        {
          "id": "entity-uuid",
          "type": "entity",
          "label": "paracetamol",
          "secondary": null
        },
        {
          "id": "source-uuid",
          "type": "source",
          "label": "Paracetamol Efficacy Study",
          "secondary": "study (2023)"
        }
      ]
    }
    ```
    """
    service = SearchService(db)

    request = SearchSuggestionRequest(
        query=query,
        types=types,
        limit=limit,
    )

    suggestions = await service.get_suggestions(request)

    return SearchSuggestionsResponse(
        query=query,
        suggestions=suggestions,
    )
