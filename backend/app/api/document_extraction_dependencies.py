import importlib.util
from pathlib import Path

from app.api.document_extraction_schemas import (
    PubMedBulkImportRequest,
    PubMedBulkSearchRequest,
    PubMedSearchResult,
    SmartDiscoveryRequest,
)
from app.llm.client import is_llm_available
from app.services.pubmed_fetcher import PubMedArticle, PubMedFetcher
from app.utils.errors import (
    AppException,
    ErrorCode,
    LLMServiceUnavailableException,
    ValidationException,
)


def _get_test_support_module():
    """
    Load deterministic extraction test support on demand.

    These helpers intentionally live under `backend.tests.support` so runtime
    API code does not own test scaffolding directly. The lazy import keeps the
    dependency explicit while only activating it in testing-oriented paths.
    """
    support_path = Path(__file__).resolve().parents[2] / "tests" / "support" / "document_extraction_support.py"
    spec = importlib.util.spec_from_file_location("document_extraction_support", support_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load test support module at {support_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def calculate_relevance(text: str, entity_names: list[str]) -> float:
    from app.services.document_extraction_discovery import calculate_relevance as _calculate_relevance

    return _calculate_relevance(text, entity_names)


def UrlFetcher(*args, **kwargs):
    from app.services.url_fetcher import UrlFetcher as _UrlFetcher

    return _UrlFetcher(*args, **kwargs)


def infer_trust_level_from_pubmed_metadata(*args, **kwargs):
    from app.utils.source_quality import infer_trust_level_from_pubmed_metadata as _infer_trust_level

    return _infer_trust_level(*args, **kwargs)


def raise_internal_api_exception(
    *,
    message: str,
    details: str | None = None,
    context: dict[str, str] | None = None,
) -> None:
    raise AppException(
        status_code=500,
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        message=message,
        details=details,
        context=context,
    )


def require_llm() -> None:
    if not is_llm_available():
        raise LLMServiceUnavailableException(
            details="LLM service is not configured. Please set OPENAI_API_KEY."
        )


def resolve_pubmed_bulk_query(request: PubMedBulkSearchRequest) -> str:
    query_from_url = None
    if request.search_url:
        query_from_url = PubMedFetcher().extract_query_from_search_url(request.search_url)
    return _get_test_support_module().resolve_pubmed_bulk_query(
        request,
        query_from_url=query_from_url,
    )


def validate_smart_discovery_request(request: SmartDiscoveryRequest) -> None:
    if not request.entity_slugs:
        raise ValidationException(
            message="At least one entity slug must be provided",
            field="entity_slugs",
            details="Provide at least one entity slug for discovery",
        )
    if len(request.entity_slugs) > 10:
        raise ValidationException(
            message="Maximum 10 entities can be searched at once",
            field="entity_slugs",
            details="Reduce the request to 10 entity slugs or fewer",
        )


def validate_pubmed_bulk_import_request(request: PubMedBulkImportRequest) -> None:
    if not request.pmids:
        raise ValidationException(
            message="No PMIDs provided",
            field="pmids",
            details="Provide at least one PMID to import",
        )
    if len(request.pmids) > 100:
        raise ValidationException(
            message="Maximum 100 PMIDs can be imported at once",
            field="pmids",
            details="Reduce the import request to 100 PMIDs or fewer",
        )


def build_test_pubmed_articles_for_query(query: str, max_results: int) -> list[PubMedArticle]:
    return _get_test_support_module().build_test_pubmed_articles(query, max_results)


def get_test_pubmed_articles_by_pmids(pmids: list[str]) -> list[PubMedArticle]:
    return _get_test_support_module().get_test_pubmed_articles_for_pmids(pmids)


def build_pubmed_results(articles: list[PubMedArticle]) -> list[PubMedSearchResult]:
    return _get_test_support_module().build_pubmed_search_results(articles)
