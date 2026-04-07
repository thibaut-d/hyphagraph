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

import datetime
import logging
from dataclasses import dataclass
from typing import Protocol, TypeAlias
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm.client import get_llm_provider
from app.llm.schemas import ExtractedClaim, ExtractedEntity, ExtractedRelation
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.models.staged_extraction import ExtractionStatus, ExtractionType, StagedExtraction
from app.schemas.common_types import SlugEntityMap
from app.schemas.entity import EntityPrefillDraft
from app.schemas.source import (
    DocumentExtractionPreview,
    EntityLinkMatch,
    SaveExtractionRequest,
    SaveExtractionResult,
    SkippedRelationDetail,
    SourceWrite,
)
from app.services.batch_extraction_orchestrator import BatchExtractionOrchestrator
from app.services.bulk_creation_service import BulkCreationService
from app.services.entity_prefill_service import EntityPrefillService
from app.services.entity_linking_service import EntityLinkMatch as ExistingEntityLinkMatch
from app.services.entity_linking_service import EntityLinkingService
from app.services.extraction_review_service import ExtractionReviewService
from app.utils.revision_helpers import create_new_revision
from app.services.extraction_service import ExtractionService
from app.services.extraction_validation_service import ValidationResult
from app.services.pubmed_fetcher import PubMedArticle, PubMedFetcher
from app.services.source_service import SourceService
from app.services.url_fetcher import UrlFetchResult, UrlFetcher
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
        commit: bool = True,
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
        auto_materialize: bool = False,
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
        entity_prefill_drafts: dict[str, EntityPrefillDraft] | None = None,
        user_id: UUID | None,
    ) -> tuple[SlugEntityMap, list[str]]: ...

    async def bulk_create_relations(
        self,
        *,
        relations: list[ExtractedRelation],
        entity_mapping: SlugEntityMap,
        source_id: UUID,
        user_id: UUID | None,
    ) -> tuple[list[ExtractedRelation], list[UUID], list[str]]: ...


class BulkCreationServiceFactory(Protocol):
    def __call__(self, db: AsyncSession) -> BulkCreationServiceProtocol: ...


class EntityPrefillServiceProtocol(Protocol):
    async def generate_draft_for_extracted_entity(
        self,
        entity: ExtractedEntity,
        user_language: str,
    ) -> EntityPrefillDraft: ...


class EntityPrefillServiceFactory(Protocol):
    def __call__(self, db: AsyncSession) -> EntityPrefillServiceProtocol: ...


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


def _build_default_entity_prefill_service(db: AsyncSession) -> EntityPrefillService:
    return EntityPrefillService(db=db, llm_provider=get_llm_provider())


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
    commit: bool = True,
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
        commit=commit,
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

    Items scoring ≥ 0.9 with no flags are marked auto_commit_eligible; the rest
    are pending for human review. Items are NOT materialised into the knowledge
    graph here — that happens in save_extraction_to_graph, which then calls
    reconcile_staged_extractions to link the resulting IDs back.
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
        llm_provider=settings.LLM_PROVIDER,
        auto_materialize=False,
        commit=False,
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
    commit: bool = True,
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
    if commit:
        # Single commit after all pipeline steps succeed. If any step above
        # raises, the staged items are never committed and no orphaned records
        # accumulate.
        await db.commit()

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
    commit: bool = True,
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

    if commit:
        await db.commit()

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
    await ensure_source_exists(db, source_id)
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
    Create a new source revision enriched with PubMed article metadata.

    Copies the current revision and applies PubMed-sourced fields (PMID, DOI,
    URL, authors, year, journal), preserving any fields already set. Creates a
    new revision via create_new_revision so that the original revision remains
    in history and provenance is not overwritten. No-op if the source has no
    current revision.
    """
    stmt = select(SourceRevision).where(
        SourceRevision.source_id == source_id,
        SourceRevision.is_current == True,
    )
    result = await db.execute(stmt)
    revision = result.scalar_one_or_none()
    if not revision:
        return

    updated_metadata = dict(revision.source_metadata or {})
    updated_metadata.update({"pmid": article.pmid, "doi": article.doi, "source": "pubmed"})

    revision_data = {
        "kind": revision.kind,
        "title": revision.title,
        "url": article.url,
        "authors": revision.authors if revision.authors else (article.authors or []),
        "year": revision.year if revision.year else article.year,
        "origin": revision.origin if revision.origin else article.journal,
        "trust_level": revision.trust_level,
        "summary": revision.summary,
        "source_metadata": updated_metadata,
        "document_text": revision.document_text,
        "document_format": revision.document_format,
        "document_file_name": revision.document_file_name,
        "document_extracted_at": revision.document_extracted_at,
        # System enrichment — no user attribution
        "created_by_user_id": None,
    }

    await create_new_revision(
        db=db,
        revision_class=SourceRevision,
        parent_id_field="source_id",
        parent_id=source_id,
        revision_data=revision_data,
        set_as_current=True,
    )
    # No commit here — the caller owns the transaction boundary.
    # The flushed revision will be committed by store_document_in_source
    # (via SourceService.add_document_to_source) in the enclosing workflow.


def _relation_match_key(rel: ExtractedRelation) -> tuple:
    """Deterministic key for matching relations: (type, frozenset of (slug, role) pairs)."""
    return (rel.relation_type, frozenset((r.entity_slug, r.role_type) for r in rel.roles))


async def reconcile_staged_extractions(
    db: AsyncSession,
    *,
    source_id: UUID,
    approved_entity_slugs_to_id: SlugEntityMap,
    rejected_entity_slugs: set[str],
    approved_relations: list[ExtractedRelation],
    approved_relation_ids: list[UUID],
    user_id: UUID | None,
) -> list[SkippedRelationDetail]:
    """
    After save_extraction_to_graph, link staged extraction records to the newly
    created graph items and record the user's approval decision.

    - ENTITY staged extractions whose slug is in approved_entity_slugs_to_id
      → APPROVED + materialized_entity_id set
    - ENTITY staged extractions whose slug is in rejected_entity_slugs
      → REJECTED (user linked to an existing entity instead)
    - RELATION staged extractions matched by (relation_type, roles)
      → APPROVED + materialized_relation_id set
    - Claims and unmatched items remain PENDING for the human review queue.

    This is a no-op when no staged extractions exist for the source (e.g. direct
    API calls that bypass the document extraction preview).
    """
    stmt = select(StagedExtraction).where(
        StagedExtraction.source_id == source_id,
        StagedExtraction.status.in_([
            ExtractionStatus.PENDING,
            ExtractionStatus.AUTO_VERIFIED,
        ]),
    )
    result = await db.execute(stmt)
    staged_items = result.scalars().all()

    if not staged_items:
        return []

    now = datetime.datetime.now(datetime.UTC)

    # Build relation key → (index, relation_id) map; first match wins for duplicates
    relation_key_to_idx: dict[tuple, int] = {}
    for idx, rel in enumerate(approved_relations):
        key = _relation_match_key(rel)
        relation_key_to_idx.setdefault(key, idx)

    skipped_relations: list[SkippedRelationDetail] = []

    for staged in staged_items:
        if staged.extraction_type == ExtractionType.ENTITY:
            slug = staged.extraction_data.get("slug")
            if slug in approved_entity_slugs_to_id:
                staged.materialized_entity_id = approved_entity_slugs_to_id[slug]
                staged.status = ExtractionStatus.APPROVED
                staged.reviewed_by = user_id
                staged.reviewed_at = now
            elif slug in rejected_entity_slugs:
                staged.status = ExtractionStatus.REJECTED
                staged.reviewed_by = user_id
                staged.reviewed_at = now
                if staged.materialized_entity_id:
                    entity = await db.get(Entity, staged.materialized_entity_id)
                    if entity:
                        entity.is_rejected = True

        elif staged.extraction_type == ExtractionType.RELATION:
            try:
                staged_rel = ExtractedRelation(**staged.extraction_data)
                key = _relation_match_key(staged_rel)
                idx = relation_key_to_idx.get(key)
                if idx is not None and idx < len(approved_relation_ids):
                    staged.materialized_relation_id = approved_relation_ids[idx]
                    staged.status = ExtractionStatus.APPROVED
                    staged.reviewed_by = user_id
                    staged.reviewed_at = now
            except Exception as exc:
                skipped_relations.append(
                    SkippedRelationDetail(
                        extraction_id=staged.id,
                        relation_type=staged.extraction_data.get("relation_type"),
                        text_span=staged.extraction_data.get("text_span"),
                        error=str(exc),
                    )
                )
                logger.error(
                    "Could not parse staged relation data for extraction %s — skipping: %s",
                    staged.id,
                    exc,
                    exc_info=True,
                )

    if skipped_relations:
        logger.error(
            "Skipped %d staged relation(s) due to parse errors for source %s",
            len(skipped_relations),
            source_id,
        )

    await db.flush()
    return skipped_relations


async def _build_entity_prefill_drafts(
    db: AsyncSession,
    *,
    entities: list[ExtractedEntity],
    user_language: str,
    entity_prefill_service_factory: EntityPrefillServiceFactory,
) -> dict[str, EntityPrefillDraft]:
    if not entities:
        return {}

    prefill_service = entity_prefill_service_factory(db)
    drafts: dict[str, EntityPrefillDraft] = {}
    for entity in entities:
        drafts[entity.slug] = await prefill_service.generate_draft_for_extracted_entity(
            entity,
            user_language,
        )
    return drafts


async def _find_existing_entity_slugs(db: AsyncSession, slugs: list[str]) -> set[str]:
    if not slugs:
        return set()
    result = await db.execute(
        select(EntityRevision.slug).where(
            EntityRevision.slug.in_(slugs),
            EntityRevision.is_current == True,
        )
    )
    return set(result.scalars().all())


def _entity_terms_from_prefill_draft(draft: EntityPrefillDraft) -> list[EntityTerm]:
    terms: list[EntityTerm] = []
    display_order = 0
    seen: set[tuple[str, str | None]] = set()

    for language, value in draft.display_names.items():
        term = value.strip()
        normalized_language = language or None
        key = (term.casefold(), normalized_language)
        if not term or key in seen:
            continue
        terms.append(
            EntityTerm(
                term=term,
                language=normalized_language,
                display_order=display_order,
                is_display_name=True,
                term_kind="alias",
            )
        )
        seen.add(key)
        display_order += 1

    for alias in draft.aliases:
        term = alias.term.strip()
        key = (term.casefold(), alias.language)
        if not term or key in seen:
            continue
        terms.append(
            EntityTerm(
                term=term,
                language=alias.language,
                display_order=display_order,
                is_display_name=False,
                term_kind=alias.term_kind,
            )
        )
        seen.add(key)
        display_order += 1

    return terms


async def _attach_prefill_terms_to_new_entities(
    db: AsyncSession,
    *,
    original_slug_to_entity_id: SlugEntityMap,
    prefill_drafts: dict[str, EntityPrefillDraft],
    preexisting_prefill_slugs: set[str],
) -> None:
    attached_entity_ids: set[UUID] = set()
    for original_slug, draft in prefill_drafts.items():
        if draft.slug in preexisting_prefill_slugs:
            continue
        entity_id = original_slug_to_entity_id.get(original_slug)
        if entity_id is None:
            continue
        if entity_id in attached_entity_ids:
            continue
        for term in _entity_terms_from_prefill_draft(draft):
            term.entity_id = entity_id
            db.add(term)
        attached_entity_ids.add(entity_id)


async def save_extraction_to_graph(
    db: AsyncSession,
    *,
    source_id: UUID,
    request: SaveExtractionRequest,
    user_id: UUID | None,
    bulk_creation_service_factory: BulkCreationServiceFactory = BulkCreationService,
    entity_prefill_service_factory: EntityPrefillServiceFactory = _build_default_entity_prefill_service,
) -> SaveExtractionResult:
    """
    Materialise a user-confirmed extraction into the knowledge graph.

    Creates new entities (entities_to_create), merges entity links (entity_links),
    then creates all relations using the final entity mapping. Commits on success
    and returns counts and IDs in SaveExtractionResult.

    After creating graph items, reconciles any staged extraction records for this
    source: approved items are linked to their materialized IDs and marked APPROVED,
    entity_links are marked REJECTED, and unselected items remain PENDING for the
    human review queue.
    """
    await ensure_source_exists(db, source_id)

    bulk_service = bulk_creation_service_factory(db)
    entity_mapping: SlugEntityMap = {}
    all_warnings: list[str] = []
    prefill_drafts = await _build_entity_prefill_drafts(
        db,
        entities=request.entities_to_create,
        user_language=getattr(request, "user_language", "en"),
        entity_prefill_service_factory=entity_prefill_service_factory,
    )
    preexisting_prefill_slugs = await _find_existing_entity_slugs(
        db,
        [draft.slug for draft in prefill_drafts.values()],
    )

    if request.entities_to_create:
        entity_mapping, entity_warnings = await bulk_service.bulk_create_entities(
            entities=request.entities_to_create,
            entity_prefill_drafts=prefill_drafts,
            user_id=user_id,
        )
        all_warnings.extend(entity_warnings)
        await _attach_prefill_terms_to_new_entities(
            db,
            original_slug_to_entity_id=entity_mapping,
            prefill_drafts=prefill_drafts,
            preexisting_prefill_slugs=preexisting_prefill_slugs,
        )

    entity_mapping.update(request.entity_links)

    created_relations: list[ExtractedRelation] = []
    relation_ids: list[UUID] = []
    if request.relations_to_create:
        created_relations, relation_ids, relation_warnings = await bulk_service.bulk_create_relations(
            relations=request.relations_to_create,
            entity_mapping=entity_mapping,
            source_id=source_id,
            user_id=user_id,
        )
        all_warnings.extend(relation_warnings)

    await db.commit()

    # Link staged extraction records to their materialized graph items (no-op
    # if no staged extractions exist for this source).
    # Use only successfully-created relations so approved_relations and
    # approved_relation_ids remain aligned even when some entries were skipped.
    created_slug_to_id = {
        e.slug: entity_mapping[e.slug]
        for e in request.entities_to_create
        if e.slug in entity_mapping
    }
    skipped_relations = await reconcile_staged_extractions(
        db,
        source_id=source_id,
        approved_entity_slugs_to_id=created_slug_to_id,
        rejected_entity_slugs=set(request.entity_links.keys()),
        approved_relations=created_relations,
        approved_relation_ids=relation_ids,
        user_id=user_id,
    )
    await db.commit()

    return SaveExtractionResult(
        entities_created=len(request.entities_to_create),
        entities_linked=len(request.entity_links),
        relations_created=len(relation_ids),
        created_entity_ids=list(created_slug_to_id.values()),
        created_relation_ids=relation_ids,
        warnings=all_warnings,
        skipped_relations=skipped_relations,
    )
