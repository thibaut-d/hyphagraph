from __future__ import annotations

import logging
from dataclasses import dataclass
from collections.abc import Awaitable, Callable
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy import String, and_, cast, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.entity_revision import EntityRevision
from app.models.source_revision import SourceRevision
from app.models.staged_extraction import StagedExtraction
from app.models.source import Source
from app.schemas.source import DocumentExtractionPreview
from app.schemas.source import SourceWrite
from app.services.document_extraction_processing import build_extraction_preview
from app.services.pubmed_fetcher import PubMedArticle, PubMedFetcher
from app.services.source_service import SourceService

TrustLevelResolver = Callable[
    [str, str | None, int | None, str | None],
    float,
]


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
    skipped_pmids: list[str]
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


@dataclass
class BulkSourceExtractionCandidate:
    source_id: UUID
    title: str
    document_text: str


@dataclass
class BulkSourceExtractionItem:
    source_id: UUID
    title: str
    status: str
    entity_count: int = 0
    relation_count: int = 0
    needs_review_count: int = 0
    auto_verified_count: int = 0
    error: str | None = None


@dataclass
class BulkSourceExtractionSummary:
    search: str
    study_budget: int
    matched_count: int
    selected_count: int
    extracted_count: int
    failed_count: int
    skipped_count: int
    results: list[BulkSourceExtractionItem]


BulkExtractionPreviewBuilder = Callable[
    [AsyncSession, UUID, str],
    Awaitable[DocumentExtractionPreview],
]


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


async def find_unextracted_source_candidates(
    db: AsyncSession,
    *,
    search: str,
    limit: int,
) -> tuple[list[BulkSourceExtractionCandidate], int]:
    """
    Find imported studies matching search that have document text and no staged extraction.

    A source with any staged extraction row is treated as already extracted. This keeps bulk
    selection conservative and avoids duplicate staged LLM outputs.
    """
    search_term = " ".join(search.strip().split())
    search_words = search_term.split()
    already_extracted = exists().where(StagedExtraction.source_id == Source.id)
    search_conditions = []
    for word in search_words:
        search_pattern = f"%{word}%"
        search_conditions.append(
            or_(
                SourceRevision.title.ilike(search_pattern),
                SourceRevision.origin.ilike(search_pattern),
                cast(SourceRevision.authors, String).ilike(search_pattern),
                cast(SourceRevision.summary, String).ilike(search_pattern),
                SourceRevision.document_text.ilike(search_pattern),
            )
        )
    base_query = (
        select(Source.id, SourceRevision.title, SourceRevision.document_text)
        .join(SourceRevision, Source.id == SourceRevision.source_id)
        .where(SourceRevision.is_current == True)
        .where(SourceRevision.status == "confirmed")
        .where(SourceRevision.kind == "study")
        .where(SourceRevision.document_text.is_not(None))
        .where(func.length(func.trim(SourceRevision.document_text)) > 0)
        .where(~already_extracted)
        .where(and_(*search_conditions))
        .order_by(
            SourceRevision.year.desc().nullslast(),
            SourceRevision.title.asc(),
            SourceRevision.created_at.desc(),
        )
    )
    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = total_result.scalar() or 0
    rows = (await db.execute(base_query.limit(limit))).all()
    return (
        [
            BulkSourceExtractionCandidate(
                source_id=row[0],
                title=row[1],
                document_text=row[2],
            )
            for row in rows
        ],
        total,
    )


async def _default_bulk_preview_builder(
    db: AsyncSession,
    source_id: UUID,
    document_text: str,
) -> DocumentExtractionPreview:
    return await build_extraction_preview(
        db,
        source_id=source_id,
        text=document_text,
        commit=False,
    )


async def run_bulk_source_extraction(
    db: AsyncSession,
    *,
    search: str,
    study_budget: int,
    preview_builder: BulkExtractionPreviewBuilder = _default_bulk_preview_builder,
) -> BulkSourceExtractionSummary:
    candidates, matched_count = await find_unextracted_source_candidates(
        db,
        search=search,
        limit=study_budget,
    )
    results: list[BulkSourceExtractionItem] = []

    for candidate in candidates:
        try:
            preview = await preview_builder(db, candidate.source_id, candidate.document_text)
            await db.commit()
            results.append(
                BulkSourceExtractionItem(
                    source_id=candidate.source_id,
                    title=candidate.title,
                    status="extracted",
                    entity_count=preview.entity_count,
                    relation_count=preview.relation_count,
                    needs_review_count=preview.needs_review_count or 0,
                    auto_verified_count=preview.auto_verified_count or 0,
                )
            )
        except Exception as exc:
            await db.rollback()
            logger.warning(
                "Bulk extraction failed for source %s: %s",
                candidate.source_id,
                exc,
                exc_info=True,
            )
            results.append(
                BulkSourceExtractionItem(
                    source_id=candidate.source_id,
                    title=candidate.title,
                    status="failed",
                    error=str(exc) or type(exc).__name__,
                )
            )

    extracted_count = sum(1 for item in results if item.status == "extracted")
    failed_count = sum(1 for item in results if item.status == "failed")
    selected_count = len(candidates)
    return BulkSourceExtractionSummary(
        search=search,
        study_budget=study_budget,
        matched_count=matched_count,
        selected_count=selected_count,
        extracted_count=extracted_count,
        failed_count=failed_count,
        skipped_count=max(matched_count - selected_count, 0),
        results=results,
    )


async def create_source_from_pubmed_article(
    db: AsyncSession,
    *,
    article: PubMedArticle,
    user_id: UUID | None,
    trust_level: float,
    discovery_query: str | None = None,
    source_service_factory: Callable[[AsyncSession], SourceService] = SourceService,
) -> UUID:
    from datetime import datetime, timezone
    source_service = source_service_factory(db)
    metadata: dict = {
        "pmid": article.pmid,
        "doi": article.doi,
        "source": "pubmed",
        "imported_via": "bulk_import",
        "import_method": "pubmed_api",
        "imported_at": datetime.now(timezone.utc).isoformat(),
    }
    if discovery_query:
        metadata["discovery_query"] = discovery_query
    source_data = SourceWrite(
        kind="study",
        title=article.title,
        authors=article.authors,
        year=article.year,
        origin=article.journal,
        url=article.url,
        trust_level=None,  # not canonical; stored in calculated_trust_level column
        calculated_trust_level=trust_level,
        summary={"en": article.abstract} if article.abstract else None,
        source_metadata=metadata,
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


async def bulk_search_pubmed_articles(
    *,
    request_query: str,
    max_results: int,
    pubmed_fetcher_factory: Callable[[], PubMedFetcher] = PubMedFetcher,
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
    pubmed_fetcher_factory: Callable[[], PubMedFetcher] = PubMedFetcher,
    testing_mode: bool = settings.TESTING,
    build_test_articles_for_pmids: Callable[[list[str]], list[PubMedArticle]] | None = None,
    trust_level_resolver: TrustLevelResolver,
    source_service_factory: Callable[[AsyncSession], SourceService] = SourceService,
    discovery_query: str | None = None,
) -> PubMedImportSummary:
    if testing_mode and build_test_articles_for_pmids is not None:
        articles = build_test_articles_for_pmids(pmids)
    else:
        articles = await pubmed_fetcher_factory().bulk_fetch_articles(pmids)

    # Skip PMIDs already imported for this user (DF-DSC-C1)
    existing_pmids = await _find_existing_pmids(db, [a.pmid for a in articles], user_id)

    source_ids: list[UUID] = []
    failed_pmids: list[str] = []
    skipped_pmids: list[str] = []

    for article in articles:
        if article.pmid in existing_pmids:
            skipped_pmids.append(article.pmid)
            continue
        try:
            trust_level = trust_level_resolver(
                article.title,
                article.journal,
                article.year,
                article.abstract,
            )
            source_ids.append(
                await create_source_from_pubmed_article(
                    db,
                    article=article,
                    user_id=user_id,
                    trust_level=trust_level,
                    discovery_query=discovery_query,
                    source_service_factory=source_service_factory,
                )
            )
        except Exception as e:
            logger.warning(
                "Failed to import PubMed article %s: %s",
                article.pmid,
                e,
                exc_info=True,
            )
            failed_pmids.append(article.pmid)

    fetched_pmids = {article.pmid for article in articles}
    failed_pmids.extend(list(set(pmids) - fetched_pmids))

    return PubMedImportSummary(
        total_requested=len(pmids),
        sources_created=len(source_ids),
        failed_pmids=failed_pmids,
        skipped_pmids=skipped_pmids,
        source_ids=source_ids,
    )


async def run_smart_discovery(
    db: AsyncSession,
    *,
    entity_slugs: list[str],
    max_results: int,
    min_quality: float,
    databases: list[str],
    user_id: UUID | None,
    pubmed_fetcher_factory: Callable[[], PubMedFetcher] = PubMedFetcher,
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
        clause = build_entity_query_clause(entity_slug)
        if clause:
            entity_query_clauses.append(clause)
        entity_relevance_terms.append(entity_slug.replace("_", "-").replace("-", " "))

    if not entity_query_clauses:
        return SmartDiscoverySummary(
            entity_slugs=entity_slugs,
            query_used="",
            total_found=0,
            results=[],
            databases_searched=[],
        )

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
                user_id=user_id,
                pubmed_fetcher_factory=pubmed_fetcher_factory,
                trust_level_resolver=trust_level_resolver,
            )
        )

    sorted_results = sorted(
        [r for r in all_results if not r.already_imported],
        key=lambda item: (item.trust_level, item.relevance_score),
        reverse=True,
    )
    return SmartDiscoverySummary(
        entity_slugs=entity_slugs,
        query_used=query,
        total_found=len(sorted_results),
        results=sorted_results[:max_results],
        databases_searched=databases_searched,
    )


async def _run_pubmed_smart_discovery(
    db: AsyncSession,
    *,
    query: str,
    entity_relevance_terms: list[str],
    max_results: int,
    min_quality: float,
    user_id: UUID | None,
    pubmed_fetcher_factory: Callable[[], PubMedFetcher],
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
        existing_pmids = await _find_existing_pmids(db, [article.pmid for article in articles], user_id)

        for article in articles:
            trust_level = trust_level_resolver(
                article.title,
                article.journal,
                article.year,
                article.abstract,
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


async def _find_existing_pmids(
    db: AsyncSession, pmids: list[str], user_id: UUID | None
) -> set[str]:
    if not pmids:
        return set()

    requested = [str(p) for p in pmids]
    # Push both the user scope and the PMID membership filter into SQL to avoid
    # loading all of the user's sources into Python memory on each discovery call.
    pmid_col = SourceRevision.source_metadata["pmid"].as_string()
    stmt = select(pmid_col).where(
        SourceRevision.is_current == True,
        SourceRevision.created_by_user_id == user_id,
        pmid_col.in_(requested),
    )
    result = await db.execute(stmt)
    return {row[0] for row in result if row[0]}
