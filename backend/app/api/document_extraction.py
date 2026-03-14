from fastapi import APIRouter
from app.api.document_extraction_schemas import (
    PubMedBulkImportRequest,
    PubMedBulkImportResponse,
    PubMedBulkSearchRequest,
    PubMedBulkSearchResponse,
    PubMedSearchResult,
    SmartDiscoveryRequest,
    SmartDiscoveryResponse,
    SmartDiscoveryResult,
    UrlExtractionRequest,
)
from app.api.document_extraction_dependencies import (
    build_entity_query_clause as _build_entity_query_clause,
    calculate_relevance as _calculate_relevance,
)


router = APIRouter(tags=["document-extraction"])

from app.api.document_extraction_routes.discovery import (
    bulk_import_pubmed,
    bulk_search_pubmed,
    router as discovery_router,
    smart_discovery,
)
from app.api.document_extraction_routes.document import (
    extract_from_document,
    extract_from_url,
    router as document_router,
    save_extraction,
    upload_and_extract,
)

router.include_router(document_router)
router.include_router(discovery_router)
