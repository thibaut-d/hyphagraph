"""
FastAPI dependency providers for all application services.

Each factory function accepts a database session via Depends(get_db) and returns
a fully-constructed service instance. Routes should declare dependencies using
these providers rather than instantiating services directly.

Boundary rule: service construction logic lives here; route handlers stay thin.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.llm.client import is_llm_available
from app.services.document_service import DocumentService
from app.services.entity_service import EntityService
from app.services.entity_term_service import EntityTermService
from app.services.export_service import ExportService
from app.services.extraction_review_service import ExtractionReviewService
from app.services.extraction_service import ExtractionService
from app.services.metadata_extractors import MetadataExtractorFactory
from app.services.search_service import SearchService
from app.services.relation_service import RelationService
from app.services.relation_type_service import RelationTypeService
from app.services.source_service import SourceService
from app.services.typedb_export_service import TypeDBExportService
from app.utils.errors import LLMServiceUnavailableException


def get_entity_service(db: AsyncSession = Depends(get_db)) -> EntityService:
    """Return an EntityService bound to the current request's database session."""
    return EntityService(db)


def get_entity_term_service(db: AsyncSession = Depends(get_db)) -> EntityTermService:
    """Return an EntityTermService bound to the current request's database session."""
    return EntityTermService(db)


def get_source_service(db: AsyncSession = Depends(get_db)) -> SourceService:
    """Return a SourceService bound to the current request's database session."""
    return SourceService(db)


def get_export_service(db: AsyncSession = Depends(get_db)) -> ExportService:
    """Return an ExportService bound to the current request's database session."""
    return ExportService(db)


def get_search_service(db: AsyncSession = Depends(get_db)) -> SearchService:
    """Return a SearchService bound to the current request's database session."""
    return SearchService(db)


def get_typedb_export_service(db: AsyncSession = Depends(get_db)) -> TypeDBExportService:
    """Return a TypeDBExportService bound to the current request's database session."""
    return TypeDBExportService(db)


def get_relation_service(db: AsyncSession = Depends(get_db)) -> RelationService:
    """Return a RelationService bound to the current request's database session."""
    return RelationService(db)


def get_relation_type_service(db: AsyncSession = Depends(get_db)) -> RelationTypeService:
    """Return a RelationTypeService bound to the current request's database session."""
    return RelationTypeService(db)


def get_extraction_review_service(
    db: AsyncSession = Depends(get_db),
) -> ExtractionReviewService:
    """Return an ExtractionReviewService bound to the current request's database session."""
    return ExtractionReviewService(db)


def get_document_service() -> DocumentService:
    """Return a stateless DocumentService (no database session required)."""
    return DocumentService()


def get_metadata_extractor_factory() -> MetadataExtractorFactory:
    """Return a stateless MetadataExtractorFactory (no database session required)."""
    return MetadataExtractorFactory()


async def get_extraction_service(db: AsyncSession = Depends(get_db)) -> ExtractionService:
    """
    Get extraction service instance with database session.

    Raises:
        LLMServiceUnavailableException: If LLM is not configured.
    """
    if not is_llm_available():
        raise LLMServiceUnavailableException(
            details="LLM service is not configured. Please set OPENAI_API_KEY environment variable."
        )
    return ExtractionService(db=db)
