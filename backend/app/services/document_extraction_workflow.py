from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Protocol, TypeAlias
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.schemas import ExtractedClaim, ExtractedEntity, ExtractedRelation
from app.models.entity_revision import EntityRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.schemas.source import DocumentExtractionPreview, EntityLinkMatch, SaveExtractionRequest, SaveExtractionResult
from app.schemas.source import SourceWrite
from app.services.batch_extraction_orchestrator import BatchExtractionOrchestrator
from app.services.bulk_creation_service import BulkCreationService
from app.services.entity_linking_service import EntityLinkMatch as ExistingEntityLinkMatch
from app.services.entity_linking_service import EntityLinkingService
from app.services.extraction_service import ExtractionService
from app.services.extraction_validation_service import ValidationResult
from app.services.extraction_review_service import ExtractionReviewService
from app.services.pubmed_fetcher import PubMedArticle
from app.services.pubmed_fetcher import PubMedFetcher
from app.services.source_service import SourceService
from app.services.url_fetcher import UrlFetchResult
from app.services.url_fetcher import UrlFetcher
from app.utils.errors import SourceNotFoundException, ValidationException


logger = logging.getLogger(__name__)


ExtractedBatchResult: TypeAlias = tuple[
    list[ExtractedEntity],
    list[ExtractedRelation],
    list[ExtractedClaim],
    list[ValidationResult],
    list[ValidationResult],
    list[ValidationResult],
]


class SourceServiceProtocol(Protocol):
    async def add_document_to_source(
        self,
        *,
        source_id: UUID,
        document_text: str,
        document_format: str,
        document_file_name: str,
        user_id: UUID | None,
    ) -> None: ...

    async def create(self, payload: SourceWrite, user_id: UUID | None = None) -> Source: ...


class SourceServiceFactory(Protocol):
    def __call__(self, db: AsyncSession) -> SourceServiceProtocol: ...


class BatchExtractionOrchestratorProtocol(Protocol):
    async def extract_batch_with_validation_results(
        self,
        *,
        text: str,
        min_confidence: str | None = None,
        min_evidence_strength: str | None = None,
    ) -> ExtractedBatchResult: ...


class BatchExtractionOrchestratorFactory(Protocol):
    def __call__(
        self,
        *,
        db: AsyncSession,
        enable_validation: bool,
        validation_level: str,
    ) -> BatchExtractionOrchestratorProtocol: ...


class ExtractionServiceProtocol(Protocol):
    async def extract_batch_with_validation_results(self, text: str) -> ExtractedBatchResult: ...


class ExtractionServiceFactory(Protocol):
    def __call__(self, db: AsyncSession) -> ExtractionServiceProtocol: ...


class ReviewStagedItemProtocol(Protocol):
    status: str
    validation_score: float | None


class ExtractionReviewServiceProtocol(Protocol):
    async def stage_batch(
        self,
        *,
        entities: list[tuple[ExtractedEntity, ValidationResult]],
        relations: list[tuple[ExtractedRelation, ValidationResult]],
        claims: list[tuple[ExtractedClaim, ValidationResult]],
        source_id: UUID,
        llm_model: str | None = None,
        llm_provider: str | None = None,
    ) -> list[ReviewStagedItemProtocol]: ...


class ExtractionReviewServiceFactory(Protocol):
    def __call__(
        self,
        *,
        db: AsyncSession,
        auto_commit_enabled: bool,
        auto_commit_threshold: float,
        require_no_flags_for_auto_commit: bool,
    ) -> ExtractionReviewServiceProtocol: ...


class EntityLinkingServiceProtocol(Protocol):
    async def find_entity_matches(
        self,
        extracted_entities: list[ExtractedEntity],
    ) -> list[ExistingEntityLinkMatch]: ...


class EntityLinkingServiceFactory(Protocol):
    def __call__(self, db: AsyncSession) -> EntityLinkingServiceProtocol: ...


class BulkCreationServiceProtocol(Protocol):
    async def bulk_create_entities(
        self,
        *,
        entities: list[ExtractedEntity],
        source_id: UUID,
        user_id: UUID | None,
    ) -> dict[str, UUID]: ...

    async def bulk_create_relations(
        self,
        *,
        relations: list[ExtractedRelation],
        entity_mapping: dict[str, UUID],
        source_id: UUID,
        user_id: UUID | None,
    ) -> list[UUID]: ...


class BulkCreationServiceFactory(Protocol):
    def __call__(self, db: AsyncSession) -> BulkCreationServiceProtocol: ...


class PubMedFetcherProtocol(Protocol):
    def extract_pmid_from_url(self, url: str) -> str | None: ...

    async def fetch_by_pmid(self, pmid: str, skip_pmc_enrichment: bool = False) -> PubMedArticle: ...

    async def bulk_fetch_articles(
        self,
        pmids: list[str],
        skip_pmc_enrichment: bool = False,
    ) -> list[PubMedArticle]: ...

    async def search_pubmed(
        self,
        *,
        query: str,
        max_results: int,
        retstart: int = 0,
    ) -> tuple[list[str], int]: ...


class PubMedFetcherFactory(Protocol):
    def __call__(self) -> PubMedFetcherProtocol: ...


class UrlFetcherProtocol(Protocol):
    async def fetch_url(self, url: str, max_length: int | None = None) -> UrlFetchResult: ...


class UrlFetcherFactory(Protocol):
    def __call__(self) -> UrlFetcherProtocol: ...


class TrustLevelResolver(Protocol):
    def __call__(
        self,
        *,
        title: str,
        journal: str | None,
        year: int | None,
        abstract: str | None,
    ) -> float: ...


@dataclass
class ExtractedBatch:
    entities: list[ExtractedEntity]
    relations: list[ExtractedRelation]
    claims: list[ExtractedClaim]
    entity_results: list[ValidationResult]
    relation_results: list[ValidationResult]
    claim_results: list[ValidationResult]


@dataclass
class ReviewSummary:
    needs_review_count: int
    auto_verified_count: int
    avg_validation_score: float | None


@dataclass
class FetchedDocument:
    text: str
    document_format: str
    file_name: str


@dataclass
class PubMedBulkSearchSummary:
    query: str
    total_results: int
    results: list[PubMedArticle]
    retrieved_count: int


@dataclass
class PubMedImportSummary:
    total_requested: int
    sources_created: int
    failed_pmids: list[str]
    source_ids: list[UUID]


@dataclass
class SmartDiscoveryItem:
    pmid: str | None
    title: str
    authors: list[str]
    journal: str | None
    year: int | None
    doi: str | None
    url: str
    trust_level: float
    relevance_score: float
    database: str
    already_imported: bool = False


@dataclass
class SmartDiscoverySummary:
    entity_slugs: list[str]
    query_used: str
    total_found: int
    results: list[SmartDiscoveryItem]
    databases_searched: list[str]


async def load_source_document_text(db: AsyncSession, source_id: UUID) -> str:
    stmt = select(SourceRevision).where(
        SourceRevision.source_id == source_id,
        SourceRevision.is_current == True,
    )
    result = await db.execute(stmt)
    revision = result.scalar_one_or_none()

    if not revision:
        raise SourceNotFoundException(source_id=str(source_id))

    if not revision.document_text:
        raise ValidationException(
            message="Source has no uploaded document",
            details="Upload a document to this source before extracting knowledge",
            context={"source_id": str(source_id)},
        )

    return revision.document_text


async def ensure_source_exists(db: AsyncSession, source_id: UUID) -> Source:
    stmt = select(Source).where(Source.id == source_id)
    result = await db.execute(stmt)
    source = result.scalar_one_or_none()
    if not source:
        raise SourceNotFoundException(source_id=str(source_id))
    return source


async def store_document_in_source(
    db: AsyncSession,
    *,
    source_id: UUID,
    text: str,
    document_format: str,
    file_name: str,
    user_id: UUID | None,
    source_service_factory: SourceServiceFactory = SourceService,
) -> None:
    source_service = source_service_factory(db)
    await source_service.add_document_to_source(
        source_id=source_id,
        document_text=text,
        document_format=document_format,
        document_file_name=file_name,
        user_id=user_id,
    )


async def run_validated_extraction(
    db: AsyncSession,
    *,
    text: str,
    orchestrator_factory: BatchExtractionOrchestratorFactory = BatchExtractionOrchestrator,
) -> ExtractedBatch:
    orchestrator = orchestrator_factory(
        db=db,
        enable_validation=True,
        validation_level="moderate",
    )
    (
        entities,
        relations,
        claims,
        entity_results,
        relation_results,
        claim_results,
    ) = await orchestrator.extract_batch_with_validation_results(
        text=text,
        min_confidence="medium",
    )
    return ExtractedBatch(
        entities=entities,
        relations=relations,
        claims=claims,
        entity_results=entity_results,
        relation_results=relation_results,
        claim_results=claim_results,
    )


async def stage_review_batch(
    db: AsyncSession,
    *,
    source_id: UUID,
    extracted_batch: ExtractedBatch,
    review_service_factory: ExtractionReviewServiceFactory = ExtractionReviewService,
) -> ReviewSummary:
    review_service = review_service_factory(
        db=db,
        auto_commit_enabled=True,
        auto_commit_threshold=0.9,
        require_no_flags_for_auto_commit=True,
    )

    staged_items = await review_service.stage_batch(
        entities=list(zip(extracted_batch.entities, extracted_batch.entity_results)),
        relations=list(zip(extracted_batch.relations, extracted_batch.relation_results)),
        claims=list(zip(extracted_batch.claims, extracted_batch.claim_results)),
        source_id=source_id,
        llm_model=settings.OPENAI_MODEL,
        llm_provider="openai",
    )

    validation_scores = [
        item.validation_score for item in staged_items if item.validation_score is not None
    ]

    return ReviewSummary(
        needs_review_count=sum(1 for item in staged_items if item.status == "pending"),
        auto_verified_count=sum(1 for item in staged_items if item.status == "auto_verified"),
        avg_validation_score=(
            sum(validation_scores) / len(validation_scores) if validation_scores else None
        ),
    )


async def build_link_suggestions(
    db: AsyncSession,
    *,
    entities: list[ExtractedEntity],
    linking_service_factory: EntityLinkingServiceFactory = EntityLinkingService,
) -> list[EntityLinkMatch]:
    linking_service = linking_service_factory(db)
    matches = await linking_service.find_entity_matches(entities)
    return [
        EntityLinkMatch(
            extracted_slug=match.extracted_slug,
            matched_entity_id=match.matched_entity_id,
            matched_entity_slug=match.matched_entity_slug,
            confidence=match.confidence,
            match_type=match.match_type,
        )
        for match in matches
    ]


async def build_extraction_preview(
    db: AsyncSession,
    *,
    source_id: UUID,
    text: str,
    orchestrator_factory: BatchExtractionOrchestratorFactory = BatchExtractionOrchestrator,
    review_service_factory: ExtractionReviewServiceFactory = ExtractionReviewService,
    linking_service_factory: EntityLinkingServiceFactory = EntityLinkingService,
) -> DocumentExtractionPreview:
    extracted_batch = await run_validated_extraction(
        db,
        text=text,
        orchestrator_factory=orchestrator_factory,
    )
    review_summary = await stage_review_batch(
        db,
        source_id=source_id,
        extracted_batch=extracted_batch,
        review_service_factory=review_service_factory,
    )
    link_suggestions = await build_link_suggestions(
        db,
        entities=extracted_batch.entities,
        linking_service_factory=linking_service_factory,
    )

    return DocumentExtractionPreview(
        source_id=source_id,
        entities=extracted_batch.entities,
        relations=extracted_batch.relations,
        entity_count=len(extracted_batch.entities),
        relation_count=len(extracted_batch.relations),
        link_suggestions=link_suggestions,
        needs_review_count=review_summary.needs_review_count,
        auto_verified_count=review_summary.auto_verified_count,
        avg_validation_score=review_summary.avg_validation_score,
    )


async def build_extraction_preview_with_service(
    db: AsyncSession,
    *,
    source_id: UUID,
    text: str,
    extraction_service_factory: ExtractionServiceFactory = ExtractionService,
    review_service_factory: ExtractionReviewServiceFactory = ExtractionReviewService,
    linking_service_factory: EntityLinkingServiceFactory = EntityLinkingService,
) -> DocumentExtractionPreview:
    extraction_service = extraction_service_factory(db)
    (
        entities,
        relations,
        claims,
        entity_results,
        relation_results,
        claim_results,
    ) = await extraction_service.extract_batch_with_validation_results(text)

    extracted_batch = ExtractedBatch(
        entities=entities,
        relations=relations,
        claims=claims,
        entity_results=entity_results,
        relation_results=relation_results,
        claim_results=claim_results,
    )
    review_summary = await stage_review_batch(
        db,
        source_id=source_id,
        extracted_batch=extracted_batch,
        review_service_factory=review_service_factory,
    )
    link_suggestions = await build_link_suggestions(
        db,
        entities=entities,
        linking_service_factory=linking_service_factory,
    )

    return DocumentExtractionPreview(
        source_id=source_id,
        entities=entities,
        relations=relations,
        entity_count=len(entities),
        relation_count=len(relations),
        link_suggestions=link_suggestions,
        needs_review_count=review_summary.needs_review_count,
        auto_verified_count=review_summary.auto_verified_count,
        avg_validation_score=review_summary.avg_validation_score,
    )


async def fetch_document_from_url(
    db: AsyncSession,
    *,
    source_id: UUID,
    url: str,
    pubmed_fetcher_factory: PubMedFetcherFactory = PubMedFetcher,
    url_fetcher_factory: UrlFetcherFactory = UrlFetcher,
) -> FetchedDocument:
    pubmed_fetcher = pubmed_fetcher_factory()
    pmid = pubmed_fetcher.extract_pmid_from_url(url)

    if not pmid:
        fetch_result = await url_fetcher_factory().fetch_url(url)
        return FetchedDocument(
            text=fetch_result.text,
            document_format="txt",
            file_name="web_content.txt",
        )

    article = await pubmed_fetcher.fetch_by_pmid(pmid)
    source = await ensure_source_exists(db, source_id)
    if source:
        await _update_source_revision_from_pubmed(db, source_id=source_id, article=article)

    return FetchedDocument(
        text=article.full_text,
        document_format="txt",
        file_name=f"pubmed_{pmid}.txt",
    )


async def _update_source_revision_from_pubmed(
    db: AsyncSession,
    *,
    source_id: UUID,
    article: PubMedArticle,
) -> None:
    stmt = select(SourceRevision).where(
        SourceRevision.source_id == source_id,
        SourceRevision.is_current == True,
    )
    result = await db.execute(stmt)
    revision = result.scalar_one_or_none()
    if not revision:
        return

    if not revision.source_metadata:
        revision.source_metadata = {}
    revision.source_metadata.update(
        {"pmid": article.pmid, "doi": article.doi, "source": "pubmed"}
    )
    revision.url = article.url
    if not revision.authors and article.authors:
        revision.authors = article.authors
    if not revision.year and article.year:
        revision.year = article.year
    if not revision.origin and article.journal:
        revision.origin = article.journal
    await db.commit()


async def save_extraction_to_graph(
    db: AsyncSession,
    *,
    source_id: UUID,
    request: SaveExtractionRequest,
    user_id: UUID | None,
    bulk_creation_service_factory: BulkCreationServiceFactory = BulkCreationService,
) -> SaveExtractionResult:
    await ensure_source_exists(db, source_id)

    bulk_service = bulk_creation_service_factory(db)
    entity_mapping: dict[str, UUID] = {}

    if request.entities_to_create:
        entity_mapping = await bulk_service.bulk_create_entities(
            entities=request.entities_to_create,
            source_id=source_id,
            user_id=user_id,
        )

    entity_mapping.update(request.entity_links)

    relation_ids: list[UUID] = []
    if request.relations_to_create:
        relation_ids = await bulk_service.bulk_create_relations(
            relations=request.relations_to_create,
            entity_mapping=entity_mapping,
            source_id=source_id,
            user_id=user_id,
        )

    await db.commit()

    return SaveExtractionResult(
        entities_created=len(request.entities_to_create),
        entities_linked=len(request.entity_links),
        relations_created=len(relation_ids),
        created_entity_ids=list(entity_mapping.values()),
        created_relation_ids=relation_ids,
        warnings=[],
    )


async def create_source_from_pubmed_article(
    db: AsyncSession,
    *,
    article: PubMedArticle,
    user_id: UUID | None,
    trust_level: float,
    source_service_factory: SourceServiceFactory = SourceService,
) -> UUID:
    source_service = source_service_factory(db)
    source_data = SourceWrite(
        kind="study",
        title=article.title,
        authors=article.authors,
        year=article.year,
        origin=article.journal,
        url=article.url,
        trust_level=trust_level,
        summary={"en": article.abstract} if article.abstract else None,
        source_metadata={
            "pmid": article.pmid,
            "doi": article.doi,
            "source": "pubmed",
            "imported_via": "bulk_import",
        },
        created_with_llm=None,
    )
    source = await source_service.create(source_data, user_id=user_id)
    await source_service.add_document_to_source(
        source_id=source.id,
        document_text=article.full_text,
        document_format="txt",
        document_file_name=f"pubmed_{article.pmid}.txt",
        user_id=user_id,
    )
    return source.id


def calculate_relevance(text: str, entity_names: list[str]) -> float:
    text_lower = text.lower()
    mentions = sum(1 for name in entity_names if name.lower() in text_lower)
    return mentions / len(entity_names) if entity_names else 0.0


def build_entity_query_clause(entity_slug: str) -> str:
    canonical = entity_slug.strip().replace("_", "-")
    if not canonical:
        return ""

    variants: list[str] = []
    for variant in (canonical, canonical.replace("-", " ")):
        cleaned = variant.strip()
        if cleaned and cleaned not in variants:
            variants.append(cleaned)

    query_terms = [f'"{variant}"' if " " in variant else variant for variant in variants]
    if len(query_terms) == 1:
        return query_terms[0]
    return f"({' OR '.join(query_terms)})"


async def bulk_search_pubmed_articles(
    *,
    request_query: str,
    max_results: int,
    pubmed_fetcher_factory: PubMedFetcherFactory = PubMedFetcher,
    testing_mode: bool = settings.TESTING,
    build_test_articles: Callable[[str, int], list[PubMedArticle]] | None = None,
) -> PubMedBulkSearchSummary:
    if testing_mode and build_test_articles is not None:
        articles = build_test_articles(request_query, max_results)
        return PubMedBulkSearchSummary(
            query=request_query,
            total_results=len(articles),
            results=articles,
            retrieved_count=len(articles),
        )

    pubmed_fetcher = pubmed_fetcher_factory()
    pmids, total_count = await pubmed_fetcher.search_pubmed(
        query=request_query,
        max_results=max_results,
    )

    if not pmids:
        return PubMedBulkSearchSummary(
            query=request_query,
            total_results=total_count,
            results=[],
            retrieved_count=0,
        )

    articles = await pubmed_fetcher.bulk_fetch_articles(pmids)
    return PubMedBulkSearchSummary(
        query=request_query,
        total_results=total_count,
        results=articles,
        retrieved_count=len(articles),
    )


async def bulk_import_pubmed_articles(
    db: AsyncSession,
    *,
    pmids: list[str],
    user_id: UUID | None,
    pubmed_fetcher_factory: PubMedFetcherFactory = PubMedFetcher,
    testing_mode: bool = settings.TESTING,
    build_test_articles_for_pmids: Callable[[list[str]], list[PubMedArticle]] | None = None,
    trust_level_resolver: TrustLevelResolver,
    source_service_factory: SourceServiceFactory = SourceService,
) -> PubMedImportSummary:
    if testing_mode and build_test_articles_for_pmids is not None:
        articles = build_test_articles_for_pmids(pmids)
    else:
        articles = await pubmed_fetcher_factory().bulk_fetch_articles(pmids)

    source_ids: list[UUID] = []
    failed_pmids: list[str] = []

    for article in articles:
        try:
            trust_level = trust_level_resolver(
                title=article.title,
                journal=article.journal,
                year=article.year,
                abstract=article.abstract,
            )
            source_ids.append(
                await create_source_from_pubmed_article(
                    db,
                    article=article,
                    user_id=user_id,
                    trust_level=trust_level,
                    source_service_factory=source_service_factory,
                )
            )
        except Exception:
            failed_pmids.append(article.pmid)

    fetched_pmids = {article.pmid for article in articles}
    failed_pmids.extend(list(set(pmids) - fetched_pmids))

    return PubMedImportSummary(
        total_requested=len(pmids),
        sources_created=len(source_ids),
        failed_pmids=failed_pmids,
        source_ids=source_ids,
    )


async def run_smart_discovery(
    db: AsyncSession,
    *,
    entity_slugs: list[str],
    max_results: int,
    min_quality: float,
    databases: list[str],
    pubmed_fetcher_factory: PubMedFetcherFactory = PubMedFetcher,
    trust_level_resolver: TrustLevelResolver,
) -> SmartDiscoverySummary:
    entity_query_clauses: list[str] = []
    entity_relevance_terms: list[str] = []

    for slug in entity_slugs:
        stmt = select(EntityRevision.slug).where(
            EntityRevision.slug == slug,
            EntityRevision.is_current == True,
        )
        result = await db.execute(stmt)
        entity_slug = result.scalar_one_or_none() or slug
        entity_query_clauses.append(build_entity_query_clause(entity_slug))
        entity_relevance_terms.append(entity_slug.replace("_", "-").replace("-", " "))

    query = " AND ".join(entity_query_clauses)
    all_results: list[SmartDiscoveryItem] = []
    databases_searched: list[str] = []

    if "pubmed" in databases:
        databases_searched.append("pubmed")
        all_results.extend(
            await _run_pubmed_smart_discovery(
                db,
                query=query,
                entity_relevance_terms=entity_relevance_terms,
                max_results=max_results,
                min_quality=min_quality,
                pubmed_fetcher_factory=pubmed_fetcher_factory,
                trust_level_resolver=trust_level_resolver,
            )
        )

    sorted_results = sorted(
        all_results,
        key=lambda item: (item.trust_level, item.relevance_score),
        reverse=True,
    )
    return SmartDiscoverySummary(
        entity_slugs=entity_slugs,
        query_used=query,
        total_found=len(sorted_results),
        results=sorted_results,
        databases_searched=databases_searched,
    )


async def _run_pubmed_smart_discovery(
    db: AsyncSession,
    *,
    query: str,
    entity_relevance_terms: list[str],
    max_results: int,
    min_quality: float,
    pubmed_fetcher_factory: PubMedFetcherFactory,
    trust_level_resolver: TrustLevelResolver,
) -> list[SmartDiscoveryItem]:
    pubmed_fetcher = pubmed_fetcher_factory()
    batch_size = 50
    max_fetch_limit = 500
    offset = 0
    all_results: list[SmartDiscoveryItem] = []

    while offset < max_fetch_limit:
        pmids, total_count = await pubmed_fetcher.search_pubmed(
            query=query,
            max_results=batch_size,
            retstart=offset,
        )
        if not pmids:
            break

        articles = await pubmed_fetcher.bulk_fetch_articles(pmids, skip_pmc_enrichment=True)
        existing_pmids = await _find_existing_pmids(db, [article.pmid for article in articles])

        for article in articles:
            trust_level = trust_level_resolver(
                title=article.title,
                journal=article.journal,
                year=article.year,
                abstract=article.abstract,
            )
            if trust_level < min_quality:
                continue

            all_results.append(
                SmartDiscoveryItem(
                    pmid=article.pmid,
                    title=article.title,
                    authors=article.authors,
                    journal=article.journal,
                    year=article.year,
                    doi=article.doi,
                    url=article.url,
                    trust_level=trust_level,
                    relevance_score=calculate_relevance(
                        article.title + " " + (article.abstract or ""),
                        entity_relevance_terms,
                    ),
                    database="pubmed",
                    already_imported=article.pmid in existing_pmids,
                )
            )

        new_sources_count = len([result for result in all_results if not result.already_imported])
        if new_sources_count >= max_results or offset + len(pmids) >= total_count:
            break

        offset += batch_size

    return all_results


async def _find_existing_pmids(db: AsyncSession, pmids: list[str]) -> set[str]:
    if not pmids:
        return set()

    stmt = select(SourceRevision.source_metadata).where(
        SourceRevision.is_current == True,
        SourceRevision.source_metadata.is_not(None),
    )
    result = await db.execute(stmt)

    existing_pmids: set[str] = set()
    requested_pmids = {str(pmid) for pmid in pmids}
    for row in result:
        metadata = row[0]
        if metadata and isinstance(metadata, dict) and "pmid" in metadata:
            existing_pmid = str(metadata["pmid"])
            if existing_pmid in requested_pmids:
                existing_pmids.add(existing_pmid)
                if len(existing_pmids) == len(requested_pmids):
                    break

    return existing_pmids
