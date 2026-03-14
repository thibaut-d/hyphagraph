from fastapi import HTTPException, status

from app.api.document_extraction_schemas import PubMedBulkSearchRequest, PubMedSearchResult
from app.llm.client import is_llm_available
from app.services.document_extraction_workflow import build_entity_query_clause, calculate_relevance
from app.services.entity_linking_service import EntityLinkingService
from app.services.extraction_service import ExtractionService
from app.services.pubmed_fetcher import PubMedArticle, PubMedFetcher
from app.services.url_fetcher import UrlFetcher
from app.utils.errors import LLMServiceUnavailableException
from app.utils.source_quality import infer_trust_level_from_pubmed_metadata


def _get_test_support_module():
    """
    Load deterministic extraction test support on demand.

    These helpers intentionally live under `backend.tests.support` so runtime
    API code does not own test scaffolding directly. The lazy import keeps the
    dependency explicit while only activating it in testing-oriented paths.
    """
    from backend.tests.support import document_extraction_support

    return document_extraction_support


def raise_internal_api_exception(
    *,
    message: str,
    details: str | None = None,
    context: dict[str, str] | None = None,
) -> None:
    detail = message
    if details:
        detail = f"{message}: {details}"
    if context:
        detail = f"{detail} ({context})"
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


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


def build_test_pubmed_articles_for_query(query: str, max_results: int) -> list[PubMedArticle]:
    return _get_test_support_module().build_test_pubmed_articles(query, max_results)


def get_test_pubmed_articles_by_pmids(pmids: list[str]) -> list[PubMedArticle]:
    return _get_test_support_module().get_test_pubmed_articles_for_pmids(pmids)


def build_pubmed_results(articles: list[PubMedArticle]) -> list[PubMedSearchResult]:
    return _get_test_support_module().build_pubmed_search_results(articles)
