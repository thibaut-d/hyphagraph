import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.utils.rate_limit import limiter
from app.api.document_extraction_dependencies import (
    PubMedFetcher,
    build_pubmed_results,
    build_test_pubmed_articles_for_query,
    get_test_pubmed_articles_by_pmids,
    infer_trust_level_from_pubmed_metadata,
    raise_internal_api_exception,
    resolve_pubmed_bulk_query,
)
from app.api.document_extraction_schemas import (
    PubMedBulkImportRequest,
    PubMedBulkImportResponse,
    PubMedBulkSearchRequest,
    PubMedBulkSearchResponse,
    SmartDiscoveryRequest,
    SmartDiscoveryResponse,
    SmartDiscoveryResult,
)
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.document_extraction_workflow import (
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

    if not request.entity_slugs or len(request.entity_slugs) == 0:
        raise ValidationException(
            message="At least one entity slug must be provided",
            field="entity_slugs",
        )
    for slug in request.entity_slugs:
        if not slug or not slug.strip():
            raise ValidationException(
                message="Entity slugs must be non-empty strings",
                field="entity_slugs",
            )
    if len(request.entity_slugs) > 10:
        raise ValidationException(
            message="Maximum 10 entities can be searched at once",
            field="entity_slugs",
            context={"provided_count": len(request.entity_slugs), "max_count": 10},
        )
    if request.max_results < 1 or request.max_results > 100:
        raise ValidationException(
            message="max_results must be between 1 and 100",
            field="max_results",
            context={"provided_value": request.max_results, "min_value": 1, "max_value": 100},
        )
    if request.min_quality < 0.0 or request.min_quality > 1.0:
        raise ValidationException(
            message="min_quality must be between 0.0 and 1.0",
            field="min_quality",
            context={"provided_value": request.min_quality, "min_value": 0.0, "max_value": 1.0},
        )
    if not request.databases or len(request.databases) == 0:
        raise ValidationException(
            message="At least one database must be selected",
            field="databases",
        )

    supported_databases = {"pubmed"}
    invalid_databases = [
        database_name
        for database_name in request.databases
        if database_name not in supported_databases
    ]
    if invalid_databases:
        raise ValidationException(
            message="Unsupported databases",
            field="databases",
            details=(
                f"Unsupported database(s): {', '.join(invalid_databases)}. "
                f"Supported databases: {', '.join(sorted(supported_databases))}"
            ),
            context={
                "invalid_databases": invalid_databases,
                "supported_databases": list(sorted(supported_databases)),
            },
        )

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
        return SmartDiscoveryResponse(
            entity_slugs=summary.entity_slugs,
            query_used=summary.query_used,
            total_found=summary.total_found,
            results=[
                SmartDiscoveryResult(
                    pmid=item.pmid,
                    title=item.title,
                    authors=item.authors,
                    journal=item.journal,
                    year=item.year,
                    doi=item.doi,
                    url=item.url,
                    trust_level=item.trust_level,
                    relevance_score=item.relevance_score,
                    database=item.database,
                    already_imported=item.already_imported,
                )
                for item in summary.results
            ],
            databases_searched=summary.databases_searched,
        )
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

    if request.max_results < 1 or request.max_results > 100:
        raise ValidationException(
            message="max_results must be between 1 and 100",
            field="max_results",
            context={"provided_value": request.max_results, "min_value": 1, "max_value": 100},
        )

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
        return PubMedBulkSearchResponse(
            query=summary.query,
            total_results=summary.total_results,
            results=build_pubmed_results(summary.results),
            retrieved_count=summary.retrieved_count,
        )
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

    if not request.pmids:
        raise ValidationException(message="No PMIDs provided for import", field="pmids")
    if len(request.pmids) > 100:
        raise ValidationException(
            message="Maximum 100 articles can be imported at once",
            field="pmids",
            context={"provided_count": len(request.pmids), "max_count": 100},
        )

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
        return PubMedBulkImportResponse(
            total_requested=summary.total_requested,
            sources_created=summary.sources_created,
            failed_pmids=summary.failed_pmids,
            skipped_pmids=summary.skipped_pmids,
            source_ids=summary.source_ids,
        )
    except (AppException, ValidationException):
        raise
    except Exception:
        logger.exception("PubMed bulk import failed for %d PMIDs", len(request.pmids))
        raise_internal_api_exception(
            message="Failed to import PubMed articles",
            context={"pmid_count": len(request.pmids)},
        )
