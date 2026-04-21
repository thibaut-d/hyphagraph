"""
Tests for document extraction API endpoints.

Tests smart discovery, URL extraction, and PubMed bulk import.
Uses scientifically accurate fibromyalgia/chronic pain test data.
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from sqlalchemy import select


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable rate limiting when calling endpoint functions directly in unit tests."""
    from app.utils.rate_limit import limiter
    limiter._enabled = False
    yield
    limiter._enabled = True

from app.services.document_extraction_workflow import calculate_relevance
from app.api.document_extraction_routes.discovery import (
    bulk_import_pubmed,
    bulk_search_pubmed,
    smart_discovery,
)
from app.api.document_extraction_routes.document import extract_from_url
from app.api.document_extraction_schemas import (
    SmartDiscoveryRequest,
    PubMedBulkSearchRequest,
    PubMedBulkImportRequest,
    UrlExtractionRequest,
)
from app.services.pubmed_fetcher import PubMedArticle
from app.models.source_revision import SourceRevision
from app.models.staged_extraction import ExtractionStatus, ExtractionType, StagedExtraction
from app.services.source_service import SourceService
from app.schemas.source import SourceWrite
from fixtures.scientific_data import ScientificEntities


# =============================================================================
# Mock Data - PubMed Articles
# =============================================================================

MOCK_PREGABALIN_ARTICLE = PubMedArticle(
    pmid="17333346",
    title="Pregabalin for the treatment of fibromyalgia syndrome: results of a randomized, double-blind, placebo-controlled trial",
    abstract="Fibromyalgia is a chronic pain disorder. Pregabalin has demonstrated efficacy in neuropathic pain. This study evaluated pregabalin efficacy and safety in fibromyalgia.",
    authors=["Crofford LJ", "Rowbotham MC", "Mease PJ"],
    journal="Arthritis & Rheumatism",
    year=2005,
    doi="10.1002/art.20868",
    url="https://pubmed.ncbi.nlm.nih.gov/17333346/",
    full_text="Pregabalin for the treatment of fibromyalgia syndrome: results of a randomized, double-blind, placebo-controlled trial. Fibromyalgia is a chronic pain disorder. Pregabalin has demonstrated efficacy in neuropathic pain. This study evaluated pregabalin efficacy and safety in fibromyalgia.",
)

MOCK_DULOXETINE_ARTICLE = PubMedArticle(
    pmid="18059454",
    title="Duloxetine in the treatment of patients with fibromyalgia: a systematic review",
    abstract="Duloxetine is an SNRI antidepressant approved for fibromyalgia treatment. This systematic review evaluates its efficacy and safety profile.",
    authors=["Arnold LM", "Lu Y", "Crofford LJ"],
    journal="BMC Musculoskeletal Disorders",
    year=2007,
    doi="10.1186/1471-2474-8-29",
    url="https://pubmed.ncbi.nlm.nih.gov/18059454/",
    full_text="Duloxetine in the treatment of patients with fibromyalgia: a systematic review. Duloxetine is an SNRI antidepressant approved for fibromyalgia treatment. This systematic review evaluates its efficacy and safety profile.",
)

MOCK_EXERCISE_ARTICLE = PubMedArticle(
    pmid="28636287",
    title="Exercise for treating fibromyalgia syndrome",
    abstract="Aerobic exercise has demonstrated benefits in fibromyalgia. This Cochrane review systematically evaluates exercise interventions.",
    authors=["Bidonde J", "Busch AJ", "Schachter CL"],
    journal="Cochrane Database of Systematic Reviews",
    year=2017,
    doi="10.1002/14651858.CD003786.pub3",
    url="https://pubmed.ncbi.nlm.nih.gov/28636287/",
    full_text="Exercise for treating fibromyalgia syndrome. Aerobic exercise has demonstrated benefits in fibromyalgia. This Cochrane review systematically evaluates exercise interventions.",
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def mock_source(db_session, test_user):
    """Create a test source for extraction tests."""
    service = SourceService(db_session)
    source_data = SourceWrite(
        kind="study",
        title="Test Study on Fibromyalgia Treatment",
        authors=["Smith J", "Doe A"],
        year=2023,
        origin="Journal of Pain Research",
        url="https://example.com/study",
        trust_level=0.75,
        summary={"en": "A study evaluating fibromyalgia treatments"},
    )
    source = await service.create(source_data, user_id=test_user.id)
    return source


@pytest.fixture
async def test_user(db_session):
    """Create a real test user in the database."""
    from app.models.user import User
    from datetime import datetime, timezone

    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="$2b$12$hashed_password_placeholder",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


# =============================================================================
# Tests - Smart Discovery
# =============================================================================


@pytest.mark.asyncio
class TestSmartDiscovery:
    """Test intelligent source discovery based on entities."""

    async def test_smart_discovery_single_entity(self, db_session, test_user):
        """Test smart discovery with a single entity slug."""
        from app.services.entity_service import EntityService
        from app.schemas.entity import EntityWrite

        # Arrange - Create entity
        entity_service = EntityService(db_session)
        entity_data = ScientificEntities.PREGABALIN
        await entity_service.create(EntityWrite(slug=entity_data["slug"]))

        # Mock PubMed search and fetch
        with patch("app.api.document_extraction_routes.discovery.PubMedFetcher") as mock_fetcher_class:
            mock_fetcher = mock_fetcher_class.return_value
            mock_fetcher.search_pubmed = AsyncMock(return_value=(["17333346"], 1))
            mock_fetcher.bulk_fetch_articles = AsyncMock(return_value=[MOCK_PREGABALIN_ARTICLE])

            # Mock trust level calculation
            with patch(
                "app.api.document_extraction_routes.discovery.infer_trust_level_from_pubmed_metadata"
            ) as mock_trust:
                mock_trust.return_value = 0.80

                # Import the endpoint function
                # Act
                request = SmartDiscoveryRequest(
                    entity_slugs=["pregabalin"],
                    max_results=10,
                    min_quality=0.5,
                    databases=["pubmed"],
                )
                response = await smart_discovery(MagicMock(), request, db=db_session, current_user=test_user)

        # Assert
        assert response.entity_slugs == ["pregabalin"]
        assert "pregabalin" in response.query_used.lower()
        assert response.total_found == 1
        assert len(response.results) == 1
        assert response.results[0].pmid == "17333346"
        assert response.results[0].title == MOCK_PREGABALIN_ARTICLE.title
        assert response.results[0].trust_level == 0.80
        assert response.results[0].database == "pubmed"

    async def test_smart_discovery_multiple_entities(self, db_session, test_user):
        """Test smart discovery with multiple entity slugs (AND query)."""
        from app.services.entity_service import EntityService
        from app.schemas.entity import EntityWrite

        # Arrange - Create entities
        entity_service = EntityService(db_session)
        await entity_service.create(
            EntityWrite(slug=ScientificEntities.DULOXETINE["slug"])
        )
        await entity_service.create(
            EntityWrite(slug=ScientificEntities.FIBROMYALGIA["slug"])
        )

        # Mock PubMed search and fetch
        with patch("app.api.document_extraction_routes.discovery.PubMedFetcher") as mock_fetcher_class:
            mock_fetcher = mock_fetcher_class.return_value
            mock_fetcher.search_pubmed = AsyncMock(return_value=(["18059454"], 1))
            mock_fetcher.bulk_fetch_articles = AsyncMock(return_value=[MOCK_DULOXETINE_ARTICLE])

            with patch(
                "app.api.document_extraction_routes.discovery.infer_trust_level_from_pubmed_metadata"
            ) as mock_trust:
                mock_trust.return_value = 0.75

                # Act
                request = SmartDiscoveryRequest(
                    entity_slugs=["duloxetine", "fibromyalgia"],
                    max_results=10,
                    min_quality=0.5,
                    databases=["pubmed"],
                )
                response = await smart_discovery(MagicMock(), request, db=db_session, current_user=test_user)

        # Assert
        assert response.entity_slugs == ["duloxetine", "fibromyalgia"]
        query_used = response.query_used.lower()
        assert "duloxetine" in query_used
        assert "fibromyalgia" in query_used
        assert " and " in query_used
        assert response.total_found == 1
        assert response.results[0].pmid == "18059454"

    async def test_smart_discovery_quality_filtering(self, db_session, test_user):
        """Test that smart discovery filters results by minimum quality threshold."""
        from app.services.entity_service import EntityService
        from app.schemas.entity import EntityWrite

        # Arrange
        entity_service = EntityService(db_session)
        await entity_service.create(
            EntityWrite(slug=ScientificEntities.FIBROMYALGIA["slug"])
        )

        # Mock two articles with different quality scores
        with patch("app.api.document_extraction_routes.discovery.PubMedFetcher") as mock_fetcher_class:
            mock_fetcher = mock_fetcher_class.return_value
            mock_fetcher.search_pubmed = AsyncMock(return_value=(["17333346", "18059454"], 2))
            mock_fetcher.bulk_fetch_articles = AsyncMock(
                return_value=[MOCK_PREGABALIN_ARTICLE, MOCK_DULOXETINE_ARTICLE]
            )

            # First article: 0.90 (high quality, passes)
            # Second article: 0.60 (low quality, filtered out)
            with patch(
                "app.api.document_extraction_routes.discovery.infer_trust_level_from_pubmed_metadata"
            ) as mock_trust:
                mock_trust.side_effect = [0.90, 0.60]

                # Act - Set minimum quality to 0.75
                request = SmartDiscoveryRequest(
                    entity_slugs=["fibromyalgia"],
                    max_results=10,
                    min_quality=0.75,
                    databases=["pubmed"],
                )
                response = await smart_discovery(MagicMock(), request, db=db_session, current_user=test_user)

        # Assert - Only high-quality article passes filter
        assert response.total_found == 1
        assert response.results[0].pmid == "17333346"
        assert response.results[0].trust_level == 0.90

    async def test_smart_discovery_already_imported_detection(self, db_session, test_user):
        """Test that smart discovery detects already-imported sources."""
        from app.services.entity_service import EntityService
        from app.services.source_service import SourceService
        from app.schemas.entity import EntityWrite
        from app.schemas.source import SourceWrite

        # Arrange - Create entity and existing source with PMID
        entity_service = EntityService(db_session)
        await entity_service.create(
            EntityWrite(slug=ScientificEntities.PREGABALIN["slug"])
        )

        source_service = SourceService(db_session)
        existing_source = SourceWrite(
            kind="study",
            title="Existing Study",
            url="https://pubmed.ncbi.nlm.nih.gov/17333346/",
            source_metadata={"pmid": "17333346", "source": "pubmed"},
        )
        await source_service.create(existing_source, user_id=test_user.id)

        # Mock PubMed search - returns PMID that already exists
        with patch("app.api.document_extraction_routes.discovery.PubMedFetcher") as mock_fetcher_class:
            mock_fetcher = mock_fetcher_class.return_value
            mock_fetcher.search_pubmed = AsyncMock(return_value=(["17333346"], 1))
            mock_fetcher.bulk_fetch_articles = AsyncMock(return_value=[MOCK_PREGABALIN_ARTICLE])

            with patch(
                "app.api.document_extraction_routes.discovery.infer_trust_level_from_pubmed_metadata"
            ) as mock_trust:
                mock_trust.return_value = 0.80

                # Act
                request = SmartDiscoveryRequest(
                    entity_slugs=["pregabalin"],
                    max_results=10,
                    min_quality=0.5,
                    databases=["pubmed"],
                )
                response = await smart_discovery(MagicMock(), request, db=db_session, current_user=test_user)

        # Assert - Result should be marked as already imported
        assert response.total_found == 1
        assert response.results[0].pmid == "17333346"
        assert response.results[0].already_imported is True

    async def test_smart_discovery_no_entity_slugs(self, db_session, test_user):
        """Test that smart discovery raises error with no entity slugs."""
        # Act & Assert
        request = SmartDiscoveryRequest(
            entity_slugs=[],
            max_results=10,
            min_quality=0.5,
            databases=["pubmed"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await smart_discovery(MagicMock(), request, db=db_session, current_user=test_user)

        assert exc_info.value.status_code == 400
        assert "at least one entity slug" in exc_info.value.detail.lower()

    async def test_smart_discovery_too_many_entities(self, db_session, test_user):
        """Test that smart discovery rejects more than 10 entity slugs."""
        # Act & Assert
        request = SmartDiscoveryRequest(
            entity_slugs=[f"entity{i}" for i in range(11)],  # 11 entities
            max_results=10,
            min_quality=0.5,
            databases=["pubmed"],
        )

        with pytest.raises(HTTPException) as exc_info:
            await smart_discovery(MagicMock(), request, db=db_session, current_user=test_user)

        assert exc_info.value.status_code == 400
        assert "maximum 10 entities" in exc_info.value.detail.lower()


# =============================================================================
# Tests - PubMed Bulk Search
# =============================================================================


@pytest.mark.asyncio
class TestPubMedBulkSearch:
    """Test PubMed bulk search endpoint."""

    async def test_bulk_search_with_query(self, db_session, test_user):
        """Test bulk search with direct query string."""
        # Mock PubMed search and fetch
        with patch("app.api.document_extraction_routes.discovery.PubMedFetcher") as mock_fetcher_class:
            mock_fetcher = mock_fetcher_class.return_value
            mock_fetcher.search_pubmed = AsyncMock(return_value=(["17333346", "18059454"], 150))
            mock_fetcher.bulk_fetch_articles = AsyncMock(
                return_value=[MOCK_PREGABALIN_ARTICLE, MOCK_DULOXETINE_ARTICLE]
            )

            # Act
            request = PubMedBulkSearchRequest(
                query="fibromyalgia AND treatment",
                max_results=10,
            )
            response = await bulk_search_pubmed(MagicMock(), request, db=db_session, current_user=test_user)

        # Assert
        assert response.query == "fibromyalgia AND treatment"
        assert response.total_results == 150
        assert response.retrieved_count == 2
        assert len(response.results) == 2
        assert response.results[0].pmid == "17333346"
        assert response.results[1].pmid == "18059454"

    async def test_bulk_search_with_url(self, db_session, test_user):
        """Test bulk search with PubMed URL (extracts query from URL)."""
        # Mock PubMed fetcher
        with patch("app.api.document_extraction_routes.discovery.PubMedFetcher") as mock_fetcher_class:
            mock_fetcher = mock_fetcher_class.return_value
            mock_fetcher.extract_query_from_search_url = MagicMock(return_value="fibromyalgia")
            mock_fetcher.search_pubmed = AsyncMock(return_value=(["17333346"], 50))
            mock_fetcher.bulk_fetch_articles = AsyncMock(return_value=[MOCK_PREGABALIN_ARTICLE])

            # Act
            request = PubMedBulkSearchRequest(
                search_url="https://pubmed.ncbi.nlm.nih.gov/?term=fibromyalgia",
                max_results=5,
            )
            response = await bulk_search_pubmed(MagicMock(), request, db=db_session, current_user=test_user)

        # Assert
        assert response.query == "fibromyalgia"
        assert response.total_results == 50
        assert response.retrieved_count == 1

    async def test_bulk_search_no_results(self, db_session, test_user):
        """Test bulk search with query that returns no results."""
        # Mock PubMed search returning no results
        with patch("app.api.document_extraction_routes.discovery.PubMedFetcher") as mock_fetcher_class:
            mock_fetcher = mock_fetcher_class.return_value
            mock_fetcher.search_pubmed = AsyncMock(return_value=([], 0))

            # Act
            request = PubMedBulkSearchRequest(
                query="nonexistent_query_xyz",
                max_results=10,
            )
            response = await bulk_search_pubmed(MagicMock(), request, db=db_session, current_user=test_user)

        # Assert
        assert response.query == "nonexistent_query_xyz"
        assert response.total_results == 0
        assert response.retrieved_count == 0
        assert len(response.results) == 0

    async def test_bulk_search_no_query_or_url(self, db_session, test_user):
        """Test bulk search raises error when neither query nor URL provided."""
        # Act & Assert
        request = PubMedBulkSearchRequest(max_results=10)

        with pytest.raises(HTTPException) as exc_info:
            await bulk_search_pubmed(MagicMock(), request, db=db_session, current_user=test_user)

        assert exc_info.value.status_code == 400
        assert "query" in exc_info.value.detail.lower()


# =============================================================================
# Tests - PubMed Bulk Import
# =============================================================================


@pytest.mark.asyncio
class TestPubMedBulkImport:
    """Test PubMed bulk import endpoint."""

    async def test_bulk_import_creates_sources(self, db_session, test_user):
        """Test bulk import creates sources for each PMID."""
        # Mock PubMed fetcher
        with patch("app.api.document_extraction_routes.discovery.PubMedFetcher") as mock_fetcher_class:
            mock_fetcher = mock_fetcher_class.return_value
            mock_fetcher.bulk_fetch_articles = AsyncMock(
                return_value=[MOCK_PREGABALIN_ARTICLE, MOCK_DULOXETINE_ARTICLE]
            )

            # Mock trust level calculation
            with patch(
                "app.api.document_extraction_routes.discovery.infer_trust_level_from_pubmed_metadata"
            ) as mock_trust:
                mock_trust.return_value = 0.75

                # Act
                request = PubMedBulkImportRequest(pmids=["17333346", "18059454"])
                response = await bulk_import_pubmed(MagicMock(), request, db=db_session, current_user=test_user)

        # Assert
        assert response.total_requested == 2
        assert response.sources_created == 2
        assert len(response.source_ids) == 2
        assert len(response.failed_pmids) == 0

        # Verify sources were created in database
        from app.services.source_service import SourceService

        source_service = SourceService(db_session)
        source1 = await source_service.get(response.source_ids[0])
        assert "Pregabalin" in source1.title
        assert source1.source_metadata["pmid"] == "17333346"

    async def test_bulk_import_no_pmids(self, db_session, test_user):
        """Test bulk import raises error with no PMIDs."""
        # Act & Assert
        request = PubMedBulkImportRequest(pmids=[])

        with pytest.raises(HTTPException) as exc_info:
            await bulk_import_pubmed(MagicMock(), request, db=db_session, current_user=test_user)

        assert exc_info.value.status_code == 400
        assert "no pmids" in exc_info.value.detail.lower()

    async def test_bulk_import_too_many_pmids(self, db_session, test_user):
        """Test bulk import rejects more than 100 PMIDs."""
        # Act & Assert
        request = PubMedBulkImportRequest(pmids=[str(i) for i in range(101)])  # 101 PMIDs

        with pytest.raises(HTTPException) as exc_info:
            await bulk_import_pubmed(MagicMock(), request, db=db_session, current_user=test_user)

        assert exc_info.value.status_code == 400
        assert "maximum 100" in exc_info.value.detail.lower()


# =============================================================================
# Tests - URL Extraction
# =============================================================================


@pytest.mark.asyncio
class TestUrlExtraction:
    """Test URL-based extraction endpoint."""

    async def test_extract_from_pubmed_url(self, db_session, mock_source, test_user):
        """Test extracting from a PubMed URL."""
        # Mock PubMed fetcher
        with patch("app.api.document_extraction_routes.document.PubMedFetcher") as mock_fetcher_class:
            mock_fetcher = mock_fetcher_class.return_value
            mock_fetcher.extract_pmid_from_url = MagicMock(return_value="17333346")
            mock_fetcher.fetch_by_pmid = AsyncMock(return_value=MOCK_PREGABALIN_ARTICLE)

            # Mock build_extraction_preview to avoid real LLM extraction
            from app.llm.schemas import ExtractedEntity as EE, ExtractedRelation as ER, ExtractedRole as ERo
            from app.schemas.source import DocumentExtractionPreview
            from app.schemas.source import EntityLinkMatch
            mock_preview = DocumentExtractionPreview(
                source_id=mock_source.id,
                entities=[EE(slug="pregabalin", summary="Anticonvulsant drug", category="drug", confidence="high", text_span="Pregabalin")],
                relations=[ER(relation_type="treats", roles=[ERo(entity_slug="pregabalin", role_type="agent"), ERo(entity_slug="fibromyalgia", role_type="target")], confidence="high", text_span="Pregabalin treats fibromyalgia")],
                entity_count=1,
                relation_count=1,
                link_suggestions=[],
                needs_review_count=0,
                auto_verified_count=1,
                avg_validation_score=1.0,
            )
            with patch(
                "app.api.document_extraction_routes.document.build_extraction_preview",
                new=AsyncMock(return_value=mock_preview),
            ):
                # Act
                request = UrlExtractionRequest(
                    url="https://pubmed.ncbi.nlm.nih.gov/17333346/"
                )
                response = await extract_from_url(
                    source_id=mock_source.id,
                    request=request,
                    db=db_session,
                    current_user=test_user,
                )

        # Assert
        assert response.source_id == mock_source.id
        assert response.entity_count == 1
        assert response.relation_count == 1
        assert response.entities[0].slug == "pregabalin"

    async def test_extract_from_url_rolls_back_document_and_staged_changes_on_preview_failure(
        self, db_session, mock_source, test_user
    ):
        fetched_document = MagicMock(
            text="Fetched source text",
            document_format="txt",
            file_name="fetched.txt",
        )

        async def failing_build_preview(db, *, source_id, text, commit=True):
            db.add(
                StagedExtraction(
                    extraction_type=ExtractionType.ENTITY,
                    status=ExtractionStatus.PENDING,
                    source_id=source_id,
                    extraction_data={
                        "slug": "rolled-back-entity",
                        "summary": "temporary",
                        "category": "drug",
                        "confidence": "high",
                        "text_span": "Fetched source text",
                    },
                    validation_score=0.8,
                    confidence_adjustment=1.0,
                    validation_flags=[],
                    auto_commit_eligible=False,
                )
            )
            await db.flush()
            raise RuntimeError("preview failed")

        with patch(
            "app.api.document_extraction_routes.document.fetch_document_from_url",
            new=AsyncMock(return_value=fetched_document),
        ), patch(
            "app.api.document_extraction_routes.document.build_extraction_preview",
            new=failing_build_preview,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await extract_from_url(
                    source_id=mock_source.id,
                    request=UrlExtractionRequest(url="https://example.com/article"),
                    db=db_session,
                    current_user=test_user,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to extract from URL"
        assert exc_info.value.error_detail.details == "preview failed"
        assert exc_info.value.error_detail.context == {
            "source_id": str(mock_source.id),
            "url": "https://example.com/article",
            "exception_type": "RuntimeError",
        }

        current_revision = await db_session.execute(
            select(SourceRevision).where(
                SourceRevision.source_id == mock_source.id,
                SourceRevision.is_current == True,
            )
        )
        revision = current_revision.scalar_one()
        assert revision.document_text is None

        staged_rows = await db_session.execute(
            select(StagedExtraction).where(StagedExtraction.source_id == mock_source.id)
        )
        assert staged_rows.scalars().all() == []


# =============================================================================
# Tests - Helper Functions
# =============================================================================


def test_calculate_relevance():
    """Test relevance score calculation."""
    # All entities mentioned
    text = "Pregabalin and Duloxetine are used to treat Fibromyalgia pain."
    entities = ["Pregabalin", "Duloxetine", "Fibromyalgia"]
    assert calculate_relevance(text, entities) == 1.0

    # Partial matches
    text = "Pregabalin is effective for treating neuropathic pain."
    entities = ["Pregabalin", "Duloxetine", "Fibromyalgia"]
    assert calculate_relevance(text, entities) == pytest.approx(0.333, abs=0.01)

    # No matches
    text = "Exercise and cognitive behavioral therapy are helpful."
    entities = ["Pregabalin", "Duloxetine"]
    assert calculate_relevance(text, entities) == 0.0

    # Case insensitive
    text = "PREGABALIN and FIBROMYALGIA"
    entities = ["Pregabalin", "Fibromyalgia"]
    assert calculate_relevance(text, entities) == 1.0

    # Empty entities list
    assert calculate_relevance("Some text", []) == 0.0
