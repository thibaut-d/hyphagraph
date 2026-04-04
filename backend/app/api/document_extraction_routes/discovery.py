import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.utils.rate_limit import limiter
from app.api.document_extraction_dependencies import (
    PubMedFetcher,
    build_test_pubmed_articles_for_query,
    get_test_pubmed_articles_by_pmids,
    raise_internal_api_exception,
    resolve_pubmed_bulk_query,
)
from app.utils.source_quality import infer_trust_level_from_pubmed_metadata
from app.api.document_extraction_schemas import (
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
from app.services.document_extraction_discovery import (
    bulk_import_pubmed_articles,
    bulk_search_pubmed_articles,
    run_smart_discovery,
)
from app.utils.errors import AppException, ValidationException


logger = logging.getLogger(__name__)

router = APIRouter(tags=["document-extraction"])


@router.post(
    "/smart-discovery",
    response_model=SmartDiscoveryResponse,
    summary="Intelligent multi-source discovery based on entities",
)
@limiter.limit("5/minute")
async def smart_discovery(
    http_request: Request,
    request: SmartDiscoveryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SmartDiscoveryResponse:
    user_email = current_user.email

    logger.info(
        f"Smart discovery requested by user {user_email}, "
        f"entities: {request.entity_slugs}, max_results: {request.max_results}, "
        f"min_quality: {request.min_quality}, databases: {request.databases}"
    )

    try:
        summary = await run_smart_discovery(
            db,
            entity_slugs=request.entity_slugs,
            max_results=request.max_results,
            min_quality=request.min_quality,
            databases=request.databases,
            user_id=current_user.id,
            pubmed_fetcher_factory=PubMedFetcher,
            trust_level_resolver=infer_trust_level_from_pubmed_metadata,
        )
        return SmartDiscoveryResponse.from_summary(summary)
    except (AppException, ValidationException):
        raise
    except Exception:
        logger.exception("Smart discovery failed for entities %s", request.entity_slugs)
        raise_internal_api_exception(
            message="Failed to perform smart discovery",
            context={"entity_slugs": request.entity_slugs},
        )


@router.post(
    "/pubmed/bulk-search",
    response_model=PubMedBulkSearchResponse,
    summary="Search PubMed and get article list",
)
@limiter.limit("5/minute")
async def bulk_search_pubmed(
    http_request: Request,
    request: PubMedBulkSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PubMedBulkSearchResponse:
    user_email = current_user.email
    query = resolve_pubmed_bulk_query(request)

    logger.info(
        f"PubMed bulk search requested by user {user_email}, "
        f"query: '{query}', max_results: {request.max_results}"
    )

    try:
        summary = await bulk_search_pubmed_articles(
            request_query=query,
            max_results=request.max_results,
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
    http_request: Request,
    request: PubMedBulkImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PubMedBulkImportResponse:
    user_email = current_user.email
    user_id = current_user.id

    logger.info(
        f"PubMed bulk import requested by user {user_email}, "
        f"importing {len(request.pmids)} articles"
    )

    try:
        summary = await bulk_import_pubmed_articles(
            db,
            pmids=request.pmids,
            user_id=user_id,
            pubmed_fetcher_factory=PubMedFetcher,
            testing_mode=settings.TESTING,
            build_test_articles_for_pmids=get_test_pubmed_articles_by_pmids,
            trust_level_resolver=infer_trust_level_from_pubmed_metadata,
        )
        return PubMedBulkImportResponse.from_summary(summary)
    except (AppException, ValidationException):
        raise
    except Exception:
        logger.exception("PubMed bulk import failed for %d PMIDs", len(request.pmids))
        raise_internal_api_exception(
            message="Failed to import PubMed articles",
            context={"pmid_count": len(request.pmids)},
        )
