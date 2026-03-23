"""
Search API endpoints for unified cross-table search.

Provides:
- POST /search - Unified search across entities, sources, and relations
- POST /search/suggestions - Autocomplete suggestions for typeahead
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.service_dependencies import get_search_service
from app.dependencies.auth import get_current_user
from app.models.user import User
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
    filters: Annotated[SearchFilters, Depends()],
    service: SearchService = Depends(get_search_service),
    _current_user: User = Depends(get_current_user),
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
    (
        results,
        total,
        entity_count,
        source_count,
        relation_count,
    ) = await service.search(filters)

    return SearchResponse(
        query=filters.query,
        results=results,
        total=total,
        limit=filters.limit,
        offset=filters.offset,
        entity_count=entity_count,
        source_count=source_count,
        relation_count=relation_count,
    )


@router.post("/suggestions", response_model=SearchSuggestionsResponse)
async def get_suggestions(
    request: Annotated[SearchSuggestionRequest, Depends()],
    service: SearchService = Depends(get_search_service),
    _current_user: User = Depends(get_current_user),
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
    suggestions = await service.get_suggestions(request)

    return SearchSuggestionsResponse(
        query=request.query,
        suggestions=suggestions,
    )
