"""
Compatibility module for document extraction workflow helpers.

Internal callers should import directly from:
- `app.services.document_extraction_discovery`
- `app.services.document_extraction_processing`

This module remains only as a narrow compatibility surface for older tests and
call sites that have not yet migrated.
"""

from app.services.document_extraction_discovery import (
    bulk_import_pubmed_articles,
    bulk_search_pubmed_articles,
    calculate_relevance,
    run_smart_discovery,
)
from app.services.document_extraction_processing import (
    build_extraction_preview,
    fetch_document_from_url,
    load_source_document_text,
    save_extraction_to_graph,
    store_document_in_source,
)

__all__ = [
    "bulk_import_pubmed_articles",
    "bulk_search_pubmed_articles",
    "build_extraction_preview",
    "calculate_relevance",
    "fetch_document_from_url",
    "load_source_document_text",
    "run_smart_discovery",
    "save_extraction_to_graph",
    "store_document_in_source",
]
