"""Thin coordinator for unified search across entities, sources, and relations."""



from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.schemas.search import (
    SearchFilters,
    SearchResult,
    SearchSuggestion,
    SearchSuggestionRequest,
)
from app.services.search.entity_search import search_entities
from app.services.search.relation_search import search_relations
from app.services.search.source_search import search_sources


class SearchService:
    """
    Service for unified search across entities, sources, and relations.

    Uses PostgreSQL full-text search for performance and ranking.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self, filters: SearchFilters
    ) -> tuple[list[SearchResult], int, int, int, int]:
        """
        Perform unified search across multiple tables.

        Args:
            filters: Search filters including query, types, pagination

        Returns:
            Tuple of (results, total_count, entity_count, source_count, relation_count)
        """
        results: list[SearchResult] = []
        entity_count = 0
        source_count = 0
        relation_count = 0

        # Determine which types to search
        search_types = filters.types or ["entity", "source", "relation"]

        # Search entities
        if "entity" in search_types:
            entity_results, entity_total = await self._search_entities(filters)
            results.extend(entity_results)
            entity_count = entity_total

        # Search sources
        if "source" in search_types:
            source_results, source_total = await self._search_sources(filters)
            results.extend(source_results)
            source_count = source_total

        # Search relations
        if "relation" in search_types:
            relation_results, relation_total = await self._search_relations(filters)
            results.extend(relation_results)
            relation_count = relation_total

        # Sort all results by relevance score (descending)
        results.sort(key=lambda r: r.relevance_score or 0, reverse=True)

        # Apply global pagination across all results
        start = filters.offset
        end = start + filters.limit
        paginated_results = results[start:end]

        total_count = entity_count + source_count + relation_count

        return (
            paginated_results,
            total_count,
            entity_count,
            source_count,
            relation_count,
        )

    async def _search_entities(self, filters: SearchFilters):
        return await search_entities(self.db, filters)

    async def _search_sources(self, filters: SearchFilters):
        return await search_sources(self.db, filters)

    async def _search_relations(self, filters: SearchFilters):
        return await search_relations(self.db, filters)

    async def get_suggestions(
        self, request: SearchSuggestionRequest
    ) -> list[SearchSuggestion]:
        """
        Get autocomplete suggestions for search queries.

        Returns quick prefix matches from entities and sources
        for typeahead autocomplete functionality.

        Args:
            request: Suggestion request with partial query

        Returns:
            List of suggestions with labels and metadata
        """
        suggestions: list[SearchSuggestion] = []
        query_lower = request.query.lower()
        search_types = request.types or ["entity", "source"]

        # Get entity suggestions (from slugs and terms)
        if "entity" in search_types:
            # Get suggestions from entity slugs
            entity_stmt = (
                select(Entity.id, EntityRevision.slug, EntityRevision.ui_category_id)
                .join(EntityRevision, Entity.id == EntityRevision.entity_id)
                .where(EntityRevision.is_current == True)
                .where(func.lower(EntityRevision.slug).startswith(query_lower))
                .order_by(EntityRevision.slug)
                .limit(request.limit)
            )

            result = await self.db.execute(entity_stmt)
            for entity_id, slug, category_id in result.all():
                suggestions.append(
                    SearchSuggestion(
                        id=entity_id,
                        type="entity",
                        label=slug,
                        secondary=None,  # Could add category label here
                    )
                )

            # Get suggestions from entity terms (if we haven't hit the limit)
            if len(suggestions) < request.limit:
                remaining = request.limit - len(suggestions)
                term_stmt = (
                    select(Entity.id, EntityTerm.term, EntityRevision.slug)
                    .join(Entity, EntityTerm.entity_id == Entity.id)
                    .join(EntityRevision, Entity.id == EntityRevision.entity_id)
                    .where(EntityRevision.is_current == True)
                    .where(func.lower(EntityTerm.term).startswith(query_lower))
                    .order_by(EntityTerm.term)
                    .limit(remaining)
                )

                result = await self.db.execute(term_stmt)
                for entity_id, term, slug in result.all():
                    suggestions.append(
                        SearchSuggestion(
                            id=entity_id,
                            type="entity",
                            label=term,
                            secondary=f"→ {slug}",  # Show which entity this term belongs to
                        )
                    )

        # Get source suggestions
        if "source" in search_types and len(suggestions) < request.limit:
            remaining = request.limit - len(suggestions)
            source_stmt = (
                select(
                    Source.id, SourceRevision.title, SourceRevision.kind, SourceRevision.year
                )
                .join(SourceRevision, Source.id == SourceRevision.source_id)
                .where(SourceRevision.is_current == True)
                .where(func.lower(SourceRevision.title).startswith(query_lower))
                .order_by(SourceRevision.year.desc().nullslast(), SourceRevision.title)
                .limit(remaining)
            )

            result = await self.db.execute(source_stmt)
            for source_id, title, kind, year in result.all():
                secondary = kind
                if year:
                    secondary = f"{kind} ({year})" if kind else str(year)
                suggestions.append(
                    SearchSuggestion(
                        id=source_id, type="source", label=title, secondary=secondary
                    )
                )

        return suggestions
