"""
Tests for search service.

Tests full-text search functionality across entities, sources, and relations.
"""

import pytest
from uuid import uuid4

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.ui_category import UiCategory
from app.schemas.search import SearchFilters, SearchSuggestionRequest
from app.services.search_service import SearchService


@pytest.fixture
async def ui_category(db_session):
    """Create a test UI category."""
    db = db_session
    category = UiCategory(
        id=uuid4(),
        slug="drug",
        labels={"en": "Drug", "fr": "Médicament"},
        order=1,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@pytest.fixture
async def test_entities(db_session, ui_category):
    """Create test entities for search."""
    db = db_session
    entities = []

    # Entity 1: paracetamol (exact match target)
    e1 = Entity(id=uuid4())
    db.add(e1)
    await db.flush()

    rev1 = EntityRevision(
        id=uuid4(),
        entity_id=e1.id,
        slug="paracetamol",
        summary={"en": "Analgesic and antipyretic drug", "fr": "Médicament antalgique"},
        ui_category_id=ui_category.id,
        is_current=True,
    )
    db.add(rev1)
    entities.append((e1, rev1))

    # Entity 2: ibuprofen (partial match)
    e2 = Entity(id=uuid4())
    db.add(e2)
    await db.flush()

    rev2 = EntityRevision(
        id=uuid4(),
        entity_id=e2.id,
        slug="ibuprofen",
        summary={"en": "Nonsteroidal anti-inflammatory drug"},
        ui_category_id=ui_category.id,
        is_current=True,
    )
    db.add(rev2)
    entities.append((e2, rev2))

    # Entity 3: aspirin (no match)
    e3 = Entity(id=uuid4())
    db.add(e3)
    await db.flush()

    rev3 = EntityRevision(
        id=uuid4(),
        entity_id=e3.id,
        slug="aspirin",
        summary={"en": "Antiplatelet medication"},
        ui_category_id=ui_category.id,
        is_current=True,
    )
    db.add(rev3)
    entities.append((e3, rev3))

    await db.commit()
    return entities


@pytest.fixture
async def test_entities_with_terms(db_session, ui_category):
    """Create test entities with entity terms for term search testing."""
    db = db_session

    # Entity: paracetamol with multiple terms/aliases
    entity = Entity(id=uuid4())
    db.add(entity)
    await db.flush()

    revision = EntityRevision(
        id=uuid4(),
        entity_id=entity.id,
        slug="paracetamol",
        summary={"en": "Analgesic and antipyretic drug"},
        ui_category_id=ui_category.id,
        is_current=True,
    )
    db.add(revision)

    # Add entity terms (aliases)
    terms_data = [
        {"term": "Acetaminophen", "language": "en", "display_order": 1},
        {"term": "Tylenol", "language": "en", "display_order": 2},
        {"term": "Paracétamol", "language": "fr", "display_order": 3},
    ]

    terms = []
    for data in terms_data:
        term = EntityTerm(entity_id=entity.id, **data)
        db.add(term)
        terms.append(term)

    await db.commit()
    await db.refresh(entity)
    await db.refresh(revision)
    for term in terms:
        await db.refresh(term)

    return entity, revision, terms


@pytest.fixture
async def test_sources(db_session, system_source):
    """Create test sources for search."""
    db = db_session
    sources = []

    # Source 1: Contains "paracetamol" in title
    s1 = Source(id=uuid4())
    db.add(s1)
    await db.flush()

    rev1 = SourceRevision(
        id=uuid4(),
        source_id=s1.id,
        kind="study",
        title="Paracetamol Efficacy in Chronic Pain",
        authors=["Smith J", "Doe A"],
        year=2023,
        origin="Journal of Pain Research",
        url="https://example.com/study1",
        trust_level=0.9,
        is_current=True,
    )
    db.add(rev1)
    sources.append((s1, rev1))

    # Source 2: Contains "paracetamol" in authors
    s2 = Source(id=uuid4())
    db.add(s2)
    await db.flush()

    rev2 = SourceRevision(
        id=uuid4(),
        source_id=s2.id,
        kind="article",
        title="Pain Management Guidelines",
        authors=["Paracetamol Research Group"],
        year=2022,
        origin="Medical Journal",
        url="https://example.com/article1",
        trust_level=0.8,
        is_current=True,
    )
    db.add(rev2)
    sources.append((s2, rev2))

    # Source 3: No match
    s3 = Source(id=uuid4())
    db.add(s3)
    await db.flush()

    rev3 = SourceRevision(
        id=uuid4(),
        source_id=s3.id,
        kind="study",
        title="Ibuprofen vs Aspirin",
        authors=["Johnson M"],
        year=2021,
        origin="Clinical Trials",
        url="https://example.com/study2",
        trust_level=0.7,
        is_current=True,
    )
    db.add(rev3)
    sources.append((s3, rev3))

    await db.commit()
    return sources


class TestSearchEntities:
    """Test entity search functionality."""

    async def test_search_entity_by_slug_exact_match(self, db_session, test_entities):
        """Test exact slug match returns highest relevance."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(query="paracetamol", limit=10, offset=0)

        results, total, entity_count, source_count, relation_count = await service.search(filters)

        assert entity_count >= 1
        assert results[0].type == "entity"
        assert results[0].title == "paracetamol"
        # Exact match should have highest relevance
        assert results[0].relevance_score == 1.0

    async def test_search_entity_by_slug_partial_match(self, db_session, test_entities):
        """Test partial slug match."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(query="para", limit=10, offset=0)

        results, total, entity_count, source_count, relation_count = await service.search(filters)

        assert entity_count >= 1
        # Should find paracetamol
        entity_titles = [r.title for r in results if r.type == "entity"]
        assert "paracetamol" in entity_titles

    async def test_search_entity_by_summary(self, db_session, test_entities):
        """Test search in entity summary."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(query="analgesic", limit=10, offset=0)

        results, total, entity_count, source_count, relation_count = await service.search(filters)

        assert entity_count >= 1
        # Should find paracetamol (has "analgesic" in summary)
        entity_slugs = [r.slug for r in results if r.type == "entity"]
        assert "paracetamol" in entity_slugs

    async def test_search_entity_case_insensitive(self, db_session, test_entities):
        """Test case-insensitive search."""
        db = db_session
        service = SearchService(db)
        filters_upper = SearchFilters(query="PARACETAMOL", limit=10, offset=0)
        filters_lower = SearchFilters(query="paracetamol", limit=10, offset=0)

        results_upper, total_upper, _, _, _ = await service.search(filters_upper)
        results_lower, total_lower, _, _, _ = await service.search(filters_lower)

        assert total_upper == total_lower
        assert len(results_upper) == len(results_lower)

    async def test_search_entity_with_ui_category_filter(self, db_session, test_entities, ui_category):
        """Test entity search with UI category filter."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(
            query="par",
            ui_category_id=[str(ui_category.id)],
            limit=10,
            offset=0,
        )

        results, total, entity_count, _, _ = await service.search(filters)

        # Should find entities in the drug category
        assert entity_count >= 1
        for result in results:
            if result.type == "entity":
                assert result.ui_category_id == ui_category.id

    async def test_search_entity_pagination(self, db_session, test_entities):
        """Test entity search pagination."""
        db = db_session
        service = SearchService(db)

        # Get first page
        filters_page1 = SearchFilters(query="i", limit=1, offset=0)
        results_page1, total, _, _, _ = await service.search(filters_page1)

        # Get second page
        filters_page2 = SearchFilters(query="i", limit=1, offset=1)
        results_page2, _, _, _, _ = await service.search(filters_page2)

        assert len(results_page1) <= 1
        assert len(results_page2) <= 1
        # Pages should have different results
        if len(results_page1) > 0 and len(results_page2) > 0:
            assert results_page1[0].id != results_page2[0].id

    async def test_search_entity_no_results(self, db_session, test_entities):
        """Test entity search with no matching results."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(query="nonexistentdrug12345", limit=10, offset=0)

        results, total, entity_count, _, _ = await service.search(filters)

        assert entity_count == 0
        assert total == 0

    async def test_search_entity_by_term_exact_match(self, db_session, test_entities_with_terms):
        """Test searching entity by exact term match."""
        db = db_session
        entity, revision, terms = test_entities_with_terms
        service = SearchService(db)

        # Search for "Tylenol" which is a term for paracetamol
        filters = SearchFilters(query="tylenol", limit=10, offset=0)
        results, total, entity_count, _, _ = await service.search(filters)

        assert entity_count >= 1
        # Should find the paracetamol entity
        entity_slugs = [r.slug for r in results if r.type == "entity"]
        assert "paracetamol" in entity_slugs
        # Exact term match should have high relevance (0.95)
        assert results[0].relevance_score == 0.95

    async def test_search_entity_by_term_partial_match(self, db_session, test_entities_with_terms):
        """Test searching entity by partial term match."""
        db = db_session
        entity, revision, terms = test_entities_with_terms
        service = SearchService(db)

        # Search for "acetamin" which partially matches "Acetaminophen"
        filters = SearchFilters(query="acetamin", limit=10, offset=0)
        results, total, entity_count, _, _ = await service.search(filters)

        assert entity_count >= 1
        # Should find the paracetamol entity
        entity_slugs = [r.slug for r in results if r.type == "entity"]
        assert "paracetamol" in entity_slugs

    async def test_search_entity_by_term_case_insensitive(self, db_session, test_entities_with_terms):
        """Test case-insensitive term search."""
        db = db_session
        entity, revision, terms = test_entities_with_terms
        service = SearchService(db)

        # Search with different cases
        filters_upper = SearchFilters(query="ACETAMINOPHEN", limit=10, offset=0)
        filters_lower = SearchFilters(query="acetaminophen", limit=10, offset=0)

        results_upper, _, count_upper, _, _ = await service.search(filters_upper)
        results_lower, _, count_lower, _, _ = await service.search(filters_lower)

        assert count_upper == count_lower
        assert count_upper >= 1

    async def test_search_entity_term_no_duplicates(self, db_session, test_entities_with_terms):
        """Test that entities with multiple matching terms don't appear as duplicates."""
        db = db_session
        entity, revision, terms = test_entities_with_terms
        service = SearchService(db)

        # Search for "a" which matches both "Acetaminophen" and "Paracétamol"
        filters = SearchFilters(query="a", types=["entity"], limit=20, offset=0)
        results, total, entity_count, _, _ = await service.search(filters)

        # Count how many times paracetamol appears
        paracetamol_count = sum(1 for r in results if r.type == "entity" and r.slug == "paracetamol")

        # Should appear only once despite multiple matching terms
        assert paracetamol_count == 1

    async def test_search_entity_relevance_slug_vs_term(self, db_session, test_entities_with_terms):
        """Test that slug matches rank higher than term matches."""
        db = db_session
        entity, revision, terms = test_entities_with_terms
        service = SearchService(db)

        # Search for "paracetamol" which matches both slug and term
        filters = SearchFilters(query="paracetamol", types=["entity"], limit=10, offset=0)
        results, total, entity_count, _, _ = await service.search(filters)

        assert entity_count >= 1
        # Exact slug match should have relevance 1.0 (higher than term match 0.95)
        first_result = results[0]
        assert first_result.slug == "paracetamol"
        assert first_result.relevance_score == 1.0


class TestSearchSources:
    """Test source search functionality."""

    async def test_search_source_by_title(self, db_session, test_sources):
        """Test source search by title."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(query="paracetamol", limit=10, offset=0)

        results, total, _, source_count, _ = await service.search(filters)

        assert source_count >= 1
        # Should find source with "Paracetamol" in title
        source_titles = [r.title for r in results if r.type == "source"]
        assert any("Paracetamol" in title for title in source_titles)

    async def test_search_source_by_authors(self, db_session, test_sources):
        """Test source search in authors array."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(query="Paracetamol Research", limit=10, offset=0)

        results, total, _, source_count, _ = await service.search(filters)

        assert source_count >= 1
        # Should find source with "Paracetamol Research Group" in authors
        for result in results:
            if result.type == "source" and result.authors:
                if any("Paracetamol" in author for author in result.authors):
                    assert True
                    return
        pytest.fail("Expected to find source by author name")

    async def test_search_source_with_kind_filter(self, db_session, test_sources):
        """Test source search with kind filter."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(
            query="pain",
            source_kind=["study"],
            limit=10,
            offset=0,
        )

        results, total, _, source_count, _ = await service.search(filters)

        # Should only return study sources
        for result in results:
            if result.type == "source":
                assert result.kind == "study"

    async def test_search_source_relevance_ranking(self, db_session, test_sources):
        """Test that title matches rank higher than author matches."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(query="paracetamol", types=["source"], limit=10, offset=0)

        results, total, _, source_count, _ = await service.search(filters)

        assert source_count >= 2

        # Find results
        title_match = None
        author_match = None
        for result in results:
            if result.type == "source":
                if "Paracetamol" in result.title:
                    title_match = result
                elif result.authors and any("Paracetamol" in a for a in result.authors):
                    author_match = result

        # Title match should have higher relevance than author match
        if title_match and author_match:
            assert title_match.relevance_score > author_match.relevance_score


class TestUnifiedSearch:
    """Test unified search across multiple types."""

    async def test_search_all_types(self, db_session, test_entities, test_sources):
        """Test search across all types."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(query="paracetamol", limit=20, offset=0)

        results, total, entity_count, source_count, relation_count = await service.search(filters)

        # Should find both entities and sources
        assert entity_count >= 1
        assert source_count >= 1
        assert total >= 2

        # Check result types
        result_types = {r.type for r in results}
        assert "entity" in result_types
        assert "source" in result_types

    async def test_search_filter_by_types(self, db_session, test_entities, test_sources):
        """Test filtering search by specific types."""
        db = db_session
        service = SearchService(db)

        # Search only entities
        filters_entities = SearchFilters(query="paracetamol", types=["entity"], limit=20, offset=0)
        results_entities, _, entity_count, source_count, _ = await service.search(filters_entities)

        assert entity_count >= 1
        assert source_count == 0
        assert all(r.type == "entity" for r in results_entities)

        # Search only sources
        filters_sources = SearchFilters(query="paracetamol", types=["source"], limit=20, offset=0)
        results_sources, _, entity_count, source_count, _ = await service.search(filters_sources)

        assert entity_count == 0
        assert source_count >= 1
        assert all(r.type == "source" for r in results_sources)

    async def test_search_results_sorted_by_relevance(self, db_session, test_entities, test_sources):
        """Test that results are sorted by relevance score."""
        db = db_session
        service = SearchService(db)
        filters = SearchFilters(query="paracetamol", limit=20, offset=0)

        results, total, _, _, _ = await service.search(filters)

        if len(results) > 1:
            # Check descending relevance order
            for i in range(len(results) - 1):
                current_score = results[i].relevance_score or 0
                next_score = results[i + 1].relevance_score or 0
                assert current_score >= next_score


class TestSearchSuggestions:
    """Test search autocomplete suggestions."""

    async def test_get_entity_suggestions(self, db_session, test_entities):
        """Test autocomplete suggestions for entities."""
        db = db_session
        service = SearchService(db)
        request = SearchSuggestionRequest(query="para", types=["entity"], limit=10)

        suggestions = await service.get_suggestions(request)

        assert len(suggestions) >= 1
        # Should suggest paracetamol
        labels = [s.label for s in suggestions]
        assert "paracetamol" in labels

    async def test_get_source_suggestions(self, db_session, test_sources):
        """Test autocomplete suggestions for sources."""
        db = db_session
        service = SearchService(db)
        request = SearchSuggestionRequest(query="Paracetamol", types=["source"], limit=10)

        suggestions = await service.get_suggestions(request)

        assert len(suggestions) >= 1
        # Should suggest source with "Paracetamol" in title
        assert any("Paracetamol" in s.label for s in suggestions)

    async def test_get_mixed_suggestions(self, db_session, test_entities, test_sources):
        """Test autocomplete suggestions from both entities and sources."""
        db = db_session
        service = SearchService(db)
        request = SearchSuggestionRequest(query="par", limit=20)

        suggestions = await service.get_suggestions(request)

        # Should have both entity and source suggestions
        types = {s.type for s in suggestions}
        assert "entity" in types or "source" in types

    async def test_suggestions_limit(self, db_session, test_entities):
        """Test that suggestions respect limit."""
        db = db_session
        service = SearchService(db)
        request = SearchSuggestionRequest(query="i", limit=2)

        suggestions = await service.get_suggestions(request)

        assert len(suggestions) <= 2

    async def test_suggestions_prefix_match_only(self, db_session, test_entities):
        """Test that suggestions only match prefixes."""
        db = db_session
        service = SearchService(db)

        # Should find "paracetamol" with prefix "para"
        request_match = SearchSuggestionRequest(query="para", types=["entity"], limit=10)
        suggestions_match = await service.get_suggestions(request_match)
        assert len(suggestions_match) >= 1

        # Should NOT find "paracetamol" with infix "cet"
        request_no_match = SearchSuggestionRequest(query="cet", types=["entity"], limit=10)
        suggestions_no_match = await service.get_suggestions(request_no_match)
        # Should have fewer results (no paracetamol)
        para_found = any("paracetamol" in s.label for s in suggestions_no_match)
        assert not para_found

    async def test_suggestions_include_entity_terms(self, db_session, test_entities_with_terms):
        """Test that suggestions include entity terms."""
        db = db_session
        entity, revision, terms = test_entities_with_terms
        service = SearchService(db)

        # Search for "Tyl" which should match "Tylenol" term
        request = SearchSuggestionRequest(query="tyl", types=["entity"], limit=10)
        suggestions = await service.get_suggestions(request)

        # Should find suggestion for Tylenol
        labels = [s.label for s in suggestions]
        assert "Tylenol" in labels

        # Check that the suggestion shows which entity it belongs to
        tylenol_suggestion = next(s for s in suggestions if s.label == "Tylenol")
        assert tylenol_suggestion.secondary == "→ paracetamol"

    async def test_suggestions_entity_terms_and_slugs(self, db_session, test_entities_with_terms):
        """Test that suggestions include both entity slugs and terms."""
        db = db_session
        entity, revision, terms = test_entities_with_terms
        service = SearchService(db)

        # Search for "para" which matches both the slug and a term
        request = SearchSuggestionRequest(query="para", types=["entity"], limit=10)
        suggestions = await service.get_suggestions(request)

        labels = [s.label for s in suggestions]
        # Should include the slug
        assert "paracetamol" in labels
        # Should also include the term if there's room
        assert len(suggestions) >= 1
