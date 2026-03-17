"""
Document extraction processing — orchestration helpers.

Boundary rules:
- This module owns the multi-step extraction workflow: load document text → run LLM
  extraction → stage review items → build link suggestions → build preview → save to graph.
- All heavy orchestration (LLM calls, bulk DB writes) is delegated to injected service
  factories so individual steps remain unit-testable in isolation.
- PubMed-specific metadata enrichment lives in _update_source_revision_from_pubmed and
  is called transparently by fetch_document_from_url when a PubMed URL is detected.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeAlias
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.schemas import ExtractedClaim, ExtractedEntity, ExtractedRelation
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.schemas.common_types import SlugEntityMap
from app.schemas.source import (
    DocumentExtractionPreview,
    EntityLinkMatch,
    SaveExtractionRequest,
    SaveExtractionResult,
    SourceWrite,
)
from app.services.batch_extraction_orchestrator import BatchExtractionOrchestrator
from app.services.bulk_creation_service import BulkCreationService
from app.services.entity_linking_service import EntityLinkMatch as ExistingEntityLinkMatch
from app.services.entity_linking_service import EntityLinkingService
from app.services.extraction_review_service import ExtractionReviewService
from app.services.extraction_service import ExtractionService
from app.services.extraction_validation_service import ValidationResult
from app.services.pubmed_fetcher import PubMedArticle, PubMedFetcher
from app.services.source_service import SourceService
from app.services.url_fetcher import UrlFetchResult, UrlFetcher
from app.utils.errors import SourceNotFoundException, ValidationException


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
    ) -> SlugEntityMap: ...

    async def bulk_create_relations(
        self,
        *,
        relations: list[ExtractedRelation],
        entity_mapping: SlugEntityMap,
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


async def load_source_document_text(db: AsyncSession, source_id: UUID) -> str:
    """
    Return the document text from the current revision of source_id.

    Raises SourceNotFoundException if the source has no current revision.
    Raises ValidationException if the revision has no uploaded document text.
    """
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
    """
    Load and return the Source record for source_id.

    Raises SourceNotFoundException if no matching source exists.
    """
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
    """
    Attach a document to an existing source by creating a new source revision.

    Delegates to SourceService.add_document_to_source, creating a revision that
    includes the supplied text, format, and file name.
    """
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
    """
    Run LLM extraction with moderate validation and return the raw ExtractedBatch.

    Uses BatchExtractionOrchestrator with enable_validation=True and
    min_confidence="medium". The orchestrator handles prompt construction,
    LLM calls, and per-item validation scoring.
    """
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
    """
    Stage all extracted items for human review and return a ReviewSummary.

    Items scoring ≥ 0.9 with no flags are auto-verified; the rest enter
    pending status for human review. Returns counts and average validation score.
    """
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
    """
    Find existing-entity matches for a list of extracted entities.

    Returns EntityLinkMatch entries suitable for the DocumentExtractionPreview
    so the frontend can offer link-vs-create decisions to the user.
    """
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
    """
    Full extraction pipeline using BatchExtractionOrchestrator (validation built-in).

    Runs extraction → stages review items → builds link suggestions, returning a
    DocumentExtractionPreview for the frontend to display before saving.
    """
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
    """
    Full extraction pipeline using ExtractionService (external validation path).

    Alternative to build_extraction_preview for callers that already hold an
    ExtractionService instance. Delegates validation to the service, then stages
    review items and builds link suggestions.
    """
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
    """
    Fetch document text from a URL, with transparent PubMed handling.

    If the URL contains a PubMed ID, fetches the article via PubMedFetcher and
    backfills source metadata (PMID, DOI, authors, year, journal) onto the current
    source revision. Otherwise falls back to generic URL fetching.
    """
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
    """
    Enrich the current source revision with PubMed article metadata in-place.

    Only updates fields that are not already populated (authors, year, origin).
    Always sets PMID, DOI, and source="pubmed" in source_metadata. No-op if the
    source has no current revision.
    """
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
    """
    Materialise a user-confirmed extraction into the knowledge graph.

    Creates new entities (entities_to_create), merges entity links (entity_links),
    then creates all relations using the final entity mapping. Commits on success
    and returns counts and IDs in SaveExtractionResult.
    """
    await ensure_source_exists(db, source_id)

    bulk_service = bulk_creation_service_factory(db)
    entity_mapping: SlugEntityMap = {}

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
