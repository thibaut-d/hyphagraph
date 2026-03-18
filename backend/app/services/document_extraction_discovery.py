from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable
from uuid import UUID

logger = logging.getLogger(__name__)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.entity_revision import EntityRevision
from app.models.source_revision import SourceRevision
from app.schemas.source import SourceWrite
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


async def create_source_from_pubmed_article(
    db: AsyncSession,
    *,
    article: PubMedArticle,
    user_id: UUID | None,
    trust_level: float,
    source_service_factory: Callable[[AsyncSession], SourceService] = SourceService,
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
        source_ids=source_ids,
    )


async def run_smart_discovery(
    db: AsyncSession,
    *,
    entity_slugs: list[str],
    max_results: int,
    min_quality: float,
    databases: list[str],
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
        existing_pmids = await _find_existing_pmids(db, [article.pmid for article in articles])

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
