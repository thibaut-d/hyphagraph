"""
Search service for unified cross-table full-text search.

Uses PostgreSQL's full-text search (FTS) capabilities for fast, ranked searching
across entities, sources, and relations.

Key features:
- Full-text search with relevance ranking
- Multi-table search (entities, sources, relations)
- Type filtering
- Autocomplete suggestions
- Snippet generation with highlighted matches
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.sql import ColumnElement
from uuid import UUID
from typing import List, Optional, Tuple

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.schemas.search import (
    SearchFilters,
    SearchResult,
    EntitySearchResult,
    SourceSearchResult,
    RelationSearchResult,
    SearchSuggestion,
    SearchSuggestionRequest,
)


class SearchService:
    """
    Service for unified search across entities, sources, and relations.

    Uses PostgreSQL full-text search for performance and ranking.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(
        self, filters: SearchFilters
    ) -> Tuple[List[SearchResult], int, int, int, int]:
        """
        Perform unified search across multiple tables.

        Args:
            filters: Search filters including query, types, pagination

        Returns:
            Tuple of (results, total_count, entity_count, source_count, relation_count)
        """
        results: List[SearchResult] = []
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

    async def _search_entities(
        self, filters: SearchFilters
    ) -> Tuple[List[EntitySearchResult], int]:
        """
        Search entities using full-text search on slug, summary, and terms.

        Searches:
        - Entity slug (primary)
        - Entity summary text (all languages)
        - Entity terms/aliases

        Returns ranked results with relevance scores.
        """
        query_lower = filters.query.lower()
        search_pattern = f"%{query_lower}%"

        # Build base query with LEFT JOIN to entity terms
        # Use DISTINCT to avoid duplicates when entity has multiple matching terms
        base_query = (
            select(Entity, EntityRevision)
            .join(EntityRevision, Entity.id == EntityRevision.entity_id)
            .outerjoin(EntityTerm, Entity.id == EntityTerm.entity_id)
            .where(EntityRevision.is_current == True)
        )

        # Apply UI category filter if provided
        if filters.ui_category_id:
            category_uuids = [UUID(cat_id) for cat_id in filters.ui_category_id]
            base_query = base_query.where(
                EntityRevision.ui_category_id.in_(category_uuids)
            )

        # Full-text search conditions
        search_conditions = [
            # Search in slug (highest priority)
            func.lower(EntityRevision.slug).contains(query_lower),
        ]

        # Search in summary JSONB (all language values)
        # PostgreSQL JSONB: check if any value in the JSON object contains the query
        if filters.query:
            # Cast JSONB to text and search
            search_conditions.append(
                func.lower(func.cast(EntityRevision.summary, String)).contains(
                    query_lower
                )
            )

        # Search in entity terms (aliases/synonyms)
        if filters.query:
            search_conditions.append(
                func.lower(EntityTerm.term).contains(query_lower)
            )

        # Combine search conditions with OR
        base_query = base_query.where(or_(*search_conditions))

        # Make query distinct to avoid duplicates from multiple term matches
        base_query = base_query.distinct()

        # Calculate relevance score
        # Higher score for exact matches, prioritize slug > terms > summary
        relevance_score = case(
            (func.lower(EntityRevision.slug) == query_lower, 1.0),  # Exact slug match
            (func.lower(EntityTerm.term) == query_lower, 0.95),  # Exact term match
            (func.lower(EntityRevision.slug).contains(query_lower), 0.8),  # Slug contains
            (func.lower(EntityTerm.term).contains(query_lower), 0.7),  # Term contains
            else_=0.5,  # Summary match
        ).label("relevance")

        # Order by relevance, then by created_at
        query_with_score = base_query.add_columns(relevance_score).order_by(
            relevance_score.desc(), Entity.created_at.desc()
        )

        # Get total count before pagination
        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination
        query_with_score = query_with_score.limit(filters.limit).offset(filters.offset)

        # Execute query
        result = await self.db.execute(query_with_score)
        rows = result.all()

        # Convert to EntitySearchResult
        search_results = []
        for entity, revision, score in rows:
            # Generate snippet from summary
            snippet = None
            if revision.summary:
                # Extract first matching language or first available
                summary_text = None
                if isinstance(revision.summary, dict):
                    summary_text = next(iter(revision.summary.values()), None)
                if summary_text and isinstance(summary_text, str):
                    # Simple snippet generation (first 150 chars)
                    snippet = (
                        summary_text[:150] + "..." if len(summary_text) > 150 else summary_text
                    )

            search_results.append(
                EntitySearchResult(
                    id=entity.id,
                    type="entity",
                    title=revision.slug,  # Use slug as title
                    slug=revision.slug,
                    snippet=snippet,
                    relevance_score=float(score) if score else 0.5,
                    ui_category_id=revision.ui_category_id,
                    summary=revision.summary,
                )
            )

        return search_results, total

    async def _search_sources(
        self, filters: SearchFilters
    ) -> Tuple[List[SourceSearchResult], int]:
        """
        Search sources using full-text search on title, authors, and origin.

        Searches:
        - Source title (primary)
        - Authors (array text)
        - Origin (journal, publisher, etc.)

        Returns ranked results with relevance scores.
        """
        query_lower = filters.query.lower()

        # Build base query
        base_query = (
            select(Source, SourceRevision)
            .join(SourceRevision, Source.id == SourceRevision.source_id)
            .where(SourceRevision.is_current == True)
        )

        # Apply source kind filter if provided
        if filters.source_kind:
            base_query = base_query.where(SourceRevision.kind.in_(filters.source_kind))

        # Full-text search conditions
        search_conditions = [
            func.lower(SourceRevision.title).contains(query_lower),
        ]

        # Search in origin
        if filters.query:
            search_conditions.append(
                func.lower(SourceRevision.origin).contains(query_lower)
            )

        # Search in authors array (cast to text)
        # SQLite stores arrays as JSON strings, PostgreSQL as arrays
        # Use CAST to convert to searchable text format
        if filters.query:
            search_conditions.append(
                func.lower(
                    func.cast(SourceRevision.authors, String)
                ).contains(query_lower)
            )

        # Combine search conditions with OR
        base_query = base_query.where(or_(*search_conditions))

        # Calculate relevance score
        relevance_score = case(
            (func.lower(SourceRevision.title) == query_lower, 1.0),  # Exact title match
            (func.lower(SourceRevision.title).contains(query_lower), 0.9),  # Title contains
            (
                func.lower(func.cast(SourceRevision.authors, String)).contains(
                    query_lower
                ),
                0.7,
            ),  # Author match
            else_=0.5,  # Origin match
        ).label("relevance")

        # Order by relevance, then by year (desc), then created_at
        query_with_score = base_query.add_columns(relevance_score).order_by(
            relevance_score.desc(),
            SourceRevision.year.desc().nullslast(),
            Source.created_at.desc(),
        )

        # Get total count before pagination
        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination
        query_with_score = query_with_score.limit(filters.limit).offset(filters.offset)

        # Execute query
        result = await self.db.execute(query_with_score)
        rows = result.all()

        # Convert to SourceSearchResult
        search_results = []
        for source, revision, score in rows:
            # Generate snippet from summary
            snippet = None
            if revision.summary:
                summary_text = None
                if isinstance(revision.summary, dict):
                    summary_text = next(iter(revision.summary.values()), None)
                if summary_text and isinstance(summary_text, str):
                    snippet = (
                        summary_text[:150] + "..." if len(summary_text) > 150 else summary_text
                    )

            search_results.append(
                SourceSearchResult(
                    id=source.id,
                    type="source",
                    title=revision.title,
                    snippet=snippet,
                    relevance_score=float(score) if score else 0.5,
                    kind=revision.kind,
                    year=revision.year,
                    authors=revision.authors,
                    trust_level=revision.trust_level,
                )
            )

        return search_results, total

    async def _search_relations(
        self, filters: SearchFilters
    ) -> Tuple[List[RelationSearchResult], int]:
        """
        Search relations using full-text search on notes.

        Searches:
        - Relation notes (all languages)
        - Relation kind

        Returns ranked results with relevance scores.
        """
        query_lower = filters.query.lower()

        # Build base query
        base_query = (
            select(Relation, RelationRevision)
            .join(RelationRevision, Relation.id == RelationRevision.relation_id)
            .where(RelationRevision.is_current == True)
        )

        # Full-text search conditions
        search_conditions = []

        # Search in kind
        if filters.query:
            search_conditions.append(
                func.lower(RelationRevision.kind).contains(query_lower)
            )

        # Search in notes JSONB (all language values)
        if filters.query:
            search_conditions.append(
                func.lower(func.cast(RelationRevision.notes, String)).contains(
                    query_lower
                )
            )

        # Combine search conditions with OR
        if search_conditions:
            base_query = base_query.where(or_(*search_conditions))

        # Calculate relevance score
        relevance_score = case(
            (func.lower(RelationRevision.kind) == query_lower, 1.0),  # Exact kind match
            (func.lower(RelationRevision.kind).contains(query_lower), 0.8),  # Kind contains
            else_=0.5,  # Notes match
        ).label("relevance")

        # Order by relevance, then by created_at
        query_with_score = base_query.add_columns(relevance_score).order_by(
            relevance_score.desc(), Relation.created_at.desc()
        )

        # Get total count before pagination
        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination
        query_with_score = query_with_score.limit(filters.limit).offset(filters.offset)

        # Execute query
        result = await self.db.execute(query_with_score)
        rows = result.all()

        # Convert to RelationSearchResult
        search_results = []
        for relation, revision, score in rows:
            # Generate snippet from notes
            snippet = None
            if revision.notes:
                notes_text = None
                if isinstance(revision.notes, dict):
                    notes_text = next(iter(revision.notes.values()), None)
                if notes_text and isinstance(notes_text, str):
                    snippet = (
                        notes_text[:150] + "..." if len(notes_text) > 150 else notes_text
                    )

            search_results.append(
                RelationSearchResult(
                    id=relation.id,
                    type="relation",
                    title=revision.kind or "Relation",  # Use kind as title
                    snippet=snippet,
                    relevance_score=float(score) if score else 0.5,
                    kind=revision.kind,
                    source_id=relation.source_id,
                    entity_ids=[],  # TODO: Fetch related entity IDs from roles
                    direction=revision.direction,
                )
            )

        return search_results, total

    async def get_suggestions(
        self, request: SearchSuggestionRequest
    ) -> List[SearchSuggestion]:
        """
        Get autocomplete suggestions for search queries.

        Returns quick prefix matches from entities and sources
        for typeahead autocomplete functionality.

        Args:
            request: Suggestion request with partial query

        Returns:
            List of suggestions with labels and metadata
        """
        suggestions: List[SearchSuggestion] = []
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


# Import String for JSONB casting
from sqlalchemy import String
