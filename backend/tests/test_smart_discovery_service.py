"""
Tests for smart discovery service functions.

Covers:
- build_entity_query_clause: slug normalisation and query term assembly
- calculate_relevance: entity mention scoring
- run_smart_discovery: orchestration, query building, sorting, already_imported flag
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.document_extraction_discovery import (
    build_entity_query_clause,
    calculate_relevance,
    run_smart_discovery,
    SmartDiscoveryItem,
)
from app.services.pubmed_fetcher import PubMedArticle


# ---------------------------------------------------------------------------
# build_entity_query_clause
# ---------------------------------------------------------------------------

class TestBuildEntityQueryClause:
    def test_simple_slug_no_hyphens(self):
        """A single-word slug is returned as-is without quotes."""
        assert build_entity_query_clause("aspirin") == "aspirin"

    def test_slug_with_hyphens_produces_or_clause(self):
        """Hyphenated slug → OR clause containing the raw form and quoted spaced form."""
        result = build_entity_query_clause("type-2-diabetes")
        assert "type-2-diabetes" in result
        assert '"type 2 diabetes"' in result
        assert "OR" in result

    def test_slug_with_underscores_normalised_to_hyphens(self):
        """Underscores are converted to hyphens before building the clause."""
        result = build_entity_query_clause("type_2_diabetes")
        assert "type-2-diabetes" in result
        assert '"type 2 diabetes"' in result

    def test_empty_slug_returns_empty_string(self):
        assert build_entity_query_clause("") == ""

    def test_whitespace_only_slug_returns_empty_string(self):
        assert build_entity_query_clause("   ") == ""

    def test_single_word_no_duplicate_variants(self):
        """A word with no hyphens has identical variants — only one term, no parentheses."""
        result = build_entity_query_clause("cancer")
        assert result == "cancer"
        assert "OR" not in result
        assert "(" not in result

    def test_leading_trailing_whitespace_stripped(self):
        assert build_entity_query_clause("  aspirin  ") == "aspirin"

    def test_hyphenated_two_word_slug(self):
        result = build_entity_query_clause("heart-failure")
        assert "heart-failure" in result
        assert '"heart failure"' in result


# ---------------------------------------------------------------------------
# calculate_relevance
# ---------------------------------------------------------------------------

class TestCalculateRelevance:
    def test_all_entities_mentioned_returns_one(self):
        score = calculate_relevance("cancer aspirin study", ["cancer", "aspirin"])
        assert score == pytest.approx(1.0)

    def test_no_entities_mentioned_returns_zero(self):
        score = calculate_relevance("unrelated text here", ["cancer", "aspirin"])
        assert score == pytest.approx(0.0)

    def test_partial_mention_returns_fraction(self):
        score = calculate_relevance("cancer study without the other drug", ["cancer", "aspirin"])
        assert score == pytest.approx(0.5)

    def test_empty_entity_list_returns_zero(self):
        score = calculate_relevance("some text", [])
        assert score == pytest.approx(0.0)

    def test_case_insensitive_matching(self):
        score = calculate_relevance("CANCER aspirin study", ["cancer", "aspirin"])
        assert score == pytest.approx(1.0)

    def test_single_entity_present_returns_one(self):
        score = calculate_relevance("aspirin reduces fever", ["aspirin"])
        assert score == pytest.approx(1.0)

    def test_single_entity_absent_returns_zero(self):
        score = calculate_relevance("ibuprofen reduces fever", ["aspirin"])
        assert score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# run_smart_discovery
# ---------------------------------------------------------------------------

def _make_article(
    pmid: str,
    title: str,
    abstract: str = "Test abstract.",
    journal: str = "Test Journal",
    year: int = 2024,
) -> PubMedArticle:
    return PubMedArticle(
        pmid=pmid,
        title=title,
        abstract=abstract,
        authors=["Author A"],
        journal=journal,
        year=year,
        doi=None,
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        full_text=f"{title}\n\nAbstract:\n{abstract}",
    )


def _constant_trust(trust: float):
    """Return a trust_level_resolver that always returns a fixed value."""
    def resolver(title, journal, year, abstract):
        return trust
    return resolver


def _make_fetcher_factory(pmids: list[str], total: int, articles: list[PubMedArticle]):
    """Build a mock pubmed_fetcher_factory returning the given search results."""
    mock_fetcher = MagicMock()
    mock_fetcher.search_pubmed = AsyncMock(return_value=(pmids, total))
    mock_fetcher.bulk_fetch_articles = AsyncMock(return_value=articles)

    def factory():
        return mock_fetcher

    return factory, mock_fetcher


@pytest.mark.asyncio
class TestRunSmartDiscovery:
    async def test_single_entity_builds_query_and_returns_results(self, db_session):
        """A single entity slug produces a query and returns results from PubMed."""
        article = _make_article("11111", "Aspirin and fever")
        factory, mock_fetcher = _make_fetcher_factory(["11111"], 1, [article])

        result = await run_smart_discovery(
            db_session,
            entity_slugs=["aspirin"],
            max_results=10,
            min_quality=0.0,
            databases=["pubmed"],
            user_id=None,
            pubmed_fetcher_factory=factory,
            trust_level_resolver=_constant_trust(0.8),
        )

        assert result.entity_slugs == ["aspirin"]
        assert len(result.results) == 1
        assert result.results[0].pmid == "11111"
        assert result.results[0].trust_level == pytest.approx(0.8)
        assert "aspirin" in result.query_used

    async def test_multiple_entities_joined_with_and(self, db_session):
        """Multiple entity slugs are joined with AND in the PubMed query."""
        article = _make_article("22222", "Aspirin heart failure study")
        factory, _ = _make_fetcher_factory(["22222"], 1, [article])

        result = await run_smart_discovery(
            db_session,
            entity_slugs=["aspirin", "heart-failure"],
            max_results=10,
            min_quality=0.0,
            databases=["pubmed"],
            user_id=None,
            pubmed_fetcher_factory=factory,
            trust_level_resolver=_constant_trust(0.7),
        )

        assert " AND " in result.query_used
        assert len(result.results) == 1

    async def test_results_filtered_by_min_quality(self, db_session):
        """Articles with trust_level < min_quality are excluded from results."""
        low_article = _make_article("33333", "Low quality study")
        high_article = _make_article("44444", "High quality study")
        factory, _ = _make_fetcher_factory(
            ["33333", "44444"], 2, [low_article, high_article]
        )

        def varying_trust(title, journal, year, abstract):
            return 0.3 if "Low" in title else 0.9

        result = await run_smart_discovery(
            db_session,
            entity_slugs=["aspirin"],
            max_results=10,
            min_quality=0.5,
            databases=["pubmed"],
            user_id=None,
            pubmed_fetcher_factory=factory,
            trust_level_resolver=varying_trust,
        )

        pmids = [item.pmid for item in result.results]
        assert "44444" in pmids
        assert "33333" not in pmids

    async def test_results_sorted_by_trust_then_relevance_descending(self, db_session):
        """Results are sorted: highest trust_level first; equal trust → highest relevance first."""
        # high trust, low relevance (title doesn't mention entity)
        high_trust_low_rel = _make_article("55555", "Unrelated cardiology study")
        # low trust, high relevance (title mentions entity)
        low_trust_high_rel = _make_article("66666", "Aspirin aspirin aspirin study")

        factory, _ = _make_fetcher_factory(
            ["55555", "66666"], 2, [high_trust_low_rel, low_trust_high_rel]
        )

        def mixed_trust(title, journal, year, abstract):
            return 0.9 if "Unrelated" in title else 0.5

        result = await run_smart_discovery(
            db_session,
            entity_slugs=["aspirin"],
            max_results=10,
            min_quality=0.0,
            databases=["pubmed"],
            user_id=None,
            pubmed_fetcher_factory=factory,
            trust_level_resolver=mixed_trust,
        )

        assert len(result.results) == 2
        # Higher trust_level should be first
        assert result.results[0].trust_level >= result.results[1].trust_level

    async def test_already_imported_flag_set_for_existing_pmid(self, db_session):
        """An article whose PMID already exists in the user's sources is flagged already_imported=True."""
        from app.services.source_service import SourceService
        from app.schemas.source import SourceWrite

        # Use user_id=None to avoid FK constraint on users table
        # _find_existing_pmids queries by created_by_user_id, so None matches NULL
        user_id = None

        # Pre-import a source with this PMID
        svc = SourceService(db_session)
        await svc.create(
            SourceWrite(
                kind="article",
                title="Pre-existing study",
                url="https://pubmed.ncbi.nlm.nih.gov/77777/",
                source_metadata={"pmid": "77777"},
            ),
            user_id=user_id,
        )

        article = _make_article("77777", "Pre-existing aspirin study")
        factory, _ = _make_fetcher_factory(["77777"], 1, [article])

        result = await run_smart_discovery(
            db_session,
            entity_slugs=["aspirin"],
            max_results=10,
            min_quality=0.0,
            databases=["pubmed"],
            user_id=user_id,
            pubmed_fetcher_factory=factory,
            trust_level_resolver=_constant_trust(0.8),
        )

        assert len(result.results) == 1
        assert result.results[0].already_imported is True

    async def test_new_article_not_flagged_as_already_imported(self, db_session):
        """An article not in the DB has already_imported=False."""
        article = _make_article("88888", "Brand new aspirin study")
        factory, _ = _make_fetcher_factory(["88888"], 1, [article])

        result = await run_smart_discovery(
            db_session,
            entity_slugs=["aspirin"],
            max_results=10,
            min_quality=0.0,
            databases=["pubmed"],
            user_id=uuid4(),
            pubmed_fetcher_factory=factory,
            trust_level_resolver=_constant_trust(0.8),
        )

        assert len(result.results) == 1
        assert result.results[0].already_imported is False

    async def test_no_pubmed_in_databases_returns_empty_results(self, db_session):
        """If 'pubmed' is not in databases, no results are fetched."""
        factory, mock_fetcher = _make_fetcher_factory([], 0, [])

        result = await run_smart_discovery(
            db_session,
            entity_slugs=["aspirin"],
            max_results=10,
            min_quality=0.0,
            databases=["other_db"],
            user_id=None,
            pubmed_fetcher_factory=factory,
            trust_level_resolver=_constant_trust(0.8),
        )

        assert result.results == []
        assert result.databases_searched == []
        mock_fetcher.search_pubmed.assert_not_called()

    async def test_pubmed_in_databases_searched_list(self, db_session):
        """'pubmed' appears in databases_searched when it is queried."""
        factory, _ = _make_fetcher_factory([], 0, [])

        result = await run_smart_discovery(
            db_session,
            entity_slugs=["aspirin"],
            max_results=10,
            min_quality=0.0,
            databases=["pubmed"],
            user_id=None,
            pubmed_fetcher_factory=factory,
            trust_level_resolver=_constant_trust(0.8),
        )

        assert "pubmed" in result.databases_searched

    async def test_relevance_score_reflects_entity_mention(self, db_session):
        """Articles mentioning the entity in title/abstract receive a non-zero relevance score."""
        article_with_mention = _make_article(
            "99999",
            "Aspirin reduces inflammation",
            abstract="This study tests aspirin in patients.",
        )
        factory, _ = _make_fetcher_factory(["99999"], 1, [article_with_mention])

        result = await run_smart_discovery(
            db_session,
            entity_slugs=["aspirin"],
            max_results=10,
            min_quality=0.0,
            databases=["pubmed"],
            user_id=None,
            pubmed_fetcher_factory=factory,
            trust_level_resolver=_constant_trust(0.8),
        )

        assert len(result.results) == 1
        assert result.results[0].relevance_score > 0
