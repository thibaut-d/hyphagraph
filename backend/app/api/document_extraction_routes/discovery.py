import logging
import asyncio

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.utils.rate_limit import limiter
from app.api.document_extraction_dependencies import (
    PubMedFetcher,
    build_test_pubmed_articles_for_query,
    get_test_pubmed_articles_by_pmids,
    raise_internal_api_exception,
    require_llm,
    resolve_pubmed_bulk_query,
    validate_pubmed_bulk_import_request,
    validate_smart_discovery_request,
)
from app.utils.source_quality import infer_trust_level_from_pubmed_metadata
from app.api.document_extraction_schemas import (
    BulkSourceExtractionRequest,
    BulkSourceExtractionResponse,
    PubMedBulkImportRequest,
    PubMedBulkImportResponse,
    PubMedBulkSearchRequest,
    PubMedBulkSearchResponse,
    SmartDiscoveryRequest,
    SmartDiscoveryResponse,
)
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.long_running_job import LongRunningJob, LongRunningJobKind
from app.schemas.long_running_job import JobStartResponse
from app.services.document_extraction_discovery import (
    bulk_import_pubmed_articles,
    bulk_search_pubmed_articles,
    run_bulk_source_extraction,
    run_smart_discovery,
)
from app.services.long_running_job_service import create_job, run_job
from app.utils.errors import AppException, ValidationException


logger = logging.getLogger(__name__)

router = APIRouter(tags=["document-extraction"])


def _bulk_source_extraction_response(summary) -> BulkSourceExtractionResponse:
    return BulkSourceExtractionResponse.model_validate(
        {
            "search": summary.search,
            "study_budget": summary.study_budget,
            "matched_count": summary.matched_count,
            "selected_count": summary.selected_count,
            "extracted_count": summary.extracted_count,
            "failed_count": summary.failed_count,
            "skipped_count": summary.skipped_count,
            "results": [
                {
                    "source_id": item.source_id,
                    "title": item.title,
                    "status": item.status,
                    "entity_count": item.entity_count,
                    "relation_count": item.relation_count,
                    "needs_review_count": item.needs_review_count,
                    "auto_verified_count": item.auto_verified_count,
                    "error": item.error,
                }
                for item in summary.results
            ],
        }
    )


async def _run_smart_discovery_job(job_id):
    async with AsyncSessionLocal() as job_db:
        async def operation(db: AsyncSession, job: LongRunningJob):
            payload = SmartDiscoveryRequest.model_validate(job.request_payload)
            summary = await run_smart_discovery(
                db,
                entity_slugs=payload.entity_slugs,
                max_results=payload.max_results,
                min_quality=payload.min_quality,
                databases=payload.databases,
                user_id=job.user_id,
                pubmed_fetcher_factory=PubMedFetcher,
                trust_level_resolver=infer_trust_level_from_pubmed_metadata,
            )
            return SmartDiscoveryResponse.from_summary(summary)

        await run_job(job_db, job_id=job_id, operation=operation)


async def _run_bulk_source_extraction_job(job_id):
    async with AsyncSessionLocal() as job_db:
        async def operation(db: AsyncSession, job: LongRunningJob):
            payload = BulkSourceExtractionRequest.model_validate(job.request_payload)
            summary = await run_bulk_source_extraction(
                db,
                search=payload.search,
                study_budget=payload.study_budget,
            )
            return _bulk_source_extraction_response(summary)

        await run_job(job_db, job_id=job_id, operation=operation)


@router.post(
    "/sources/bulk-extraction/jobs",
    response_model=JobStartResponse,
    summary="Start a bulk extraction job for imported studies matching a search term",
    dependencies=[Depends(require_llm)],
)
@limiter.limit("5/minute")
async def start_bulk_source_extraction_job(
    request: Request,
    payload: BulkSourceExtractionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobStartResponse:
    job = await create_job(
        db,
        kind=LongRunningJobKind.BULK_SOURCE_EXTRACTION,
        user_id=current_user.id,
        request_payload=payload.model_dump(mode="json"),
    )
    asyncio.create_task(_run_bulk_source_extraction_job(job.id))
    return JobStartResponse(job_id=job.id, status=job.status.value)


@router.post(
    "/smart-discovery",
    response_model=SmartDiscoveryResponse,
    summary="Intelligent multi-source discovery based on entities",
)
@limiter.limit("5/minute")
async def smart_discovery(
    request: Request,
    payload: SmartDiscoveryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SmartDiscoveryResponse:
    validate_smart_discovery_request(payload)
    user_email = current_user.email

    logger.info(
        f"Smart discovery requested by user {user_email}, "
        f"entities: {payload.entity_slugs}, max_results: {payload.max_results}, "
        f"min_quality: {payload.min_quality}, databases: {payload.databases}"
    )

    try:
        summary = await run_smart_discovery(
            db,
            entity_slugs=payload.entity_slugs,
            max_results=payload.max_results,
            min_quality=payload.min_quality,
            databases=payload.databases,
            user_id=current_user.id,
            pubmed_fetcher_factory=PubMedFetcher,
            trust_level_resolver=infer_trust_level_from_pubmed_metadata,
        )
        return SmartDiscoveryResponse.from_summary(summary)
    except (AppException, ValidationException):
        raise
    except Exception:
        logger.exception("Smart discovery failed for entities %s", payload.entity_slugs)
        raise_internal_api_exception(
            message="Failed to perform smart discovery",
            context={"entity_slugs": payload.entity_slugs},
        )


@router.post(
    "/smart-discovery/jobs",
    response_model=JobStartResponse,
    summary="Start a resumable smart discovery job",
)
@limiter.limit("5/minute")
async def start_smart_discovery_job(
    request: Request,
    payload: SmartDiscoveryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobStartResponse:
    validate_smart_discovery_request(payload)
    job = await create_job(
        db,
        kind=LongRunningJobKind.SMART_DISCOVERY,
        user_id=current_user.id,
        request_payload=payload.model_dump(mode="json"),
    )
    asyncio.create_task(_run_smart_discovery_job(job.id))
    return JobStartResponse(job_id=job.id, status=job.status.value)


@router.post(
    "/pubmed/bulk-search",
    response_model=PubMedBulkSearchResponse,
    summary="Search PubMed and get article list",
)
@limiter.limit("5/minute")
async def bulk_search_pubmed(
    request: Request,
    payload: PubMedBulkSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PubMedBulkSearchResponse:
    user_email = current_user.email
    query = resolve_pubmed_bulk_query(payload)

    logger.info(
        f"PubMed bulk search requested by user {user_email}, "
        f"query: '{query}', max_results: {payload.max_results}"
    )

    try:
        summary = await bulk_search_pubmed_articles(
            request_query=query,
            max_results=payload.max_results,
            pubmed_fetcher_factory=PubMedFetcher,
            testing_mode=settings.TESTING,
            build_test_articles=build_test_pubmed_articles_for_query,
        )
        return PubMedBulkSearchResponse.from_summary(summary)
    except (AppException, ValidationException):
        raise
    except Exception:
        logger.exception("PubMed bulk search failed for query %r", query)
        raise_internal_api_exception(
            message="Failed to search PubMed",
            context={"query": query},
        )


@router.post(
    "/pubmed/bulk-import",
    response_model=PubMedBulkImportResponse,
    summary="Batch import PubMed articles as sources",
)
@limiter.limit("5/minute")
async def bulk_import_pubmed(
    request: Request,
    payload: PubMedBulkImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PubMedBulkImportResponse:
    validate_pubmed_bulk_import_request(payload)
    user_email = current_user.email
    user_id = current_user.id

    logger.info(
        f"PubMed bulk import requested by user {user_email}, "
        f"importing {len(payload.pmids)} articles"
    )

    try:
        summary = await bulk_import_pubmed_articles(
            db,
            pmids=payload.pmids,
            user_id=user_id,
            pubmed_fetcher_factory=PubMedFetcher,
            testing_mode=settings.TESTING,
            build_test_articles_for_pmids=get_test_pubmed_articles_by_pmids,
            trust_level_resolver=infer_trust_level_from_pubmed_metadata,
            discovery_query=payload.discovery_query,
        )
        return PubMedBulkImportResponse.from_summary(summary)
    except (AppException, ValidationException):
        raise
    except Exception:
        logger.exception("PubMed bulk import failed for %d PMIDs", len(payload.pmids))
        raise_internal_api_exception(
            message="Failed to import PubMed articles",
            context={"pmid_count": len(payload.pmids)},
        )
