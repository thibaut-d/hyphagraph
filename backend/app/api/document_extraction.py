"""
API endpoints for document-based knowledge extraction workflow.

Provides end-to-end document upload → extraction → linking → storage pipeline.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.source import (
    DocumentExtractionPreview,
    SaveExtractionRequest,
    SaveExtractionResult,
    EntityLinkMatch
)
from app.services.source_service import SourceService
from app.services.extraction_service import ExtractionService
from app.services.entity_linking_service import EntityLinkingService
from app.services.bulk_creation_service import BulkCreationService
from app.services.document_service import DocumentService
from app.services.pubmed_fetcher import PubMedFetcher
from app.services.url_fetcher import UrlFetcher
from app.llm.client import is_llm_available
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger(__name__)

router = APIRouter(tags=["document-extraction"])


# =============================================================================
# Request/Response Models
# =============================================================================

class UrlExtractionRequest(BaseModel):
    """Request model for URL-based extraction."""
    url: str


# =============================================================================
# Dependency: Require LLM
# =============================================================================

def require_llm():
    """Require LLM to be available for these endpoints."""
    if not is_llm_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service not available. Please configure OPENAI_API_KEY."
        )


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/sources/{source_id}/extract-from-document",
    response_model=DocumentExtractionPreview,
    summary="Extract knowledge from uploaded document",
    description="""
    Extract entities and relations from a source's uploaded document.

    Prerequisites:
    - Source must have a document uploaded via POST /sources/{source_id}/upload-document
    - LLM service must be configured (OPENAI_API_KEY)

    This endpoint:
    1. Retrieves document text from the source
    2. Extracts entities and relations using LLM
    3. Finds matches in existing knowledge graph
    4. Returns preview with link suggestions

    The user can then review the suggestions and use the save endpoint to commit.
    """,
    dependencies=[Depends(require_llm)]
)
async def extract_from_document(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentExtractionPreview:
    """Extract knowledge from source document and suggest entity links."""
    user_email = current_user.email if current_user else "system"
    logger.info(f"Document extraction requested for source {source_id} by user {user_email}")

    # Get source and check for document
    source_service = SourceService(db)

    # Get source document text
    from sqlalchemy import select
    from app.models.source_revision import SourceRevision

    stmt = select(SourceRevision).where(
        SourceRevision.source_id == source_id,
        SourceRevision.is_current == True
    )
    result = await db.execute(stmt)
    revision = result.scalar_one_or_none()

    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )

    if not revision.document_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source has no uploaded document. Upload a document first."
        )

    # Extract entities and relations
    extraction_service = ExtractionService()
    entities, relations, _ = await extraction_service.extract_batch(
        text=revision.document_text,
        min_confidence="medium"
    )

    logger.info(f"Extracted {len(entities)} entities and {len(relations)} relations from document")

    # Find entity matches in existing graph
    linking_service = EntityLinkingService(db)
    matches = await linking_service.find_entity_matches(entities)

    # Convert matches to schema format
    link_suggestions = [
        EntityLinkMatch(
            extracted_slug=m.extracted_slug,
            matched_entity_id=m.matched_entity_id,
            matched_entity_slug=m.matched_entity_slug,
            confidence=m.confidence,
            match_type=m.match_type
        )
        for m in matches
    ]

    return DocumentExtractionPreview(
        source_id=source_id,
        entities=entities,
        relations=relations,
        entity_count=len(entities),
        relation_count=len(relations),
        link_suggestions=link_suggestions
    )


@router.post(
    "/sources/{source_id}/save-extraction",
    response_model=SaveExtractionResult,
    summary="Save extracted knowledge to graph",
    description="""
    Save user-approved extracted entities and relations to the knowledge graph.

    This endpoint:
    1. Creates new entities for non-linked extractions
    2. Links extracted entities to existing entities per user's decisions
    3. Creates relations using the entity mappings
    4. Associates all created items with the source

    Request body specifies:
    - entities_to_create: Entities user wants to create as new
    - entity_links: Mapping of extracted slug → existing entity ID
    - relations_to_create: Relations to create (will auto-resolve entity IDs)

    All operations are atomic - if any step fails, nothing is committed.
    """,
    dependencies=[Depends(require_llm)]
)
async def save_extraction(
    source_id: UUID,
    request: SaveExtractionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SaveExtractionResult:
    """Save user-approved extracted knowledge to the graph."""
    logger.info(
        f"Save extraction requested for source {source_id}: "
        f"{len(request.entities_to_create)} new entities, "
        f"{len(request.entity_links)} links, "
        f"{len(request.relations_to_create)} relations"
    )

    warnings = []

    try:
        # Verify source exists
        source_service = SourceService(db)
        from app.models.source import Source
        from sqlalchemy import select

        stmt = select(Source).where(Source.id == source_id)
        result = await db.execute(stmt)
        source = result.scalar_one_or_none()

        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )

        # Create new entities
        bulk_service = BulkCreationService(db)
        entity_mapping = {}

        if request.entities_to_create:
            entity_mapping = await bulk_service.bulk_create_entities(
                entities=request.entities_to_create,
                source_id=source_id,
                user_id=current_user.id if current_user else None
            )

        # Add linked entities to mapping (extracted_slug -> existing_entity_id)
        entity_mapping.update(request.entity_links)

        # Create relations
        relation_ids = []
        if request.relations_to_create:
            relation_ids = await bulk_service.bulk_create_relations(
                relations=request.relations_to_create,
                entity_mapping=entity_mapping,
                source_id=source_id,
                user_id=current_user.id if current_user else None
            )

        created_entity_ids = list(entity_mapping.values())

        logger.info(
            f"Saved extraction: {len(created_entity_ids)} entities "
            f"(created {len(request.entities_to_create)}, linked {len(request.entity_links)}), "
            f"{len(relation_ids)} relations"
        )

        return SaveExtractionResult(
            entities_created=len(request.entities_to_create),
            entities_linked=len(request.entity_links),
            relations_created=len(relation_ids),
            created_entity_ids=created_entity_ids,
            created_relation_ids=relation_ids,
            warnings=warnings
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save extraction: {str(e)}"
        )


@router.post(
    "/sources/{source_id}/upload-and-extract",
    response_model=DocumentExtractionPreview,
    summary="Upload document and extract knowledge in one step",
    description="""
    Convenience endpoint that combines document upload and knowledge extraction.

    This endpoint:
    1. Accepts file upload (PDF or TXT)
    2. Extracts text from the document
    3. Stores document content in the source
    4. Extracts entities and relations using LLM
    5. Finds matches in existing knowledge graph
    6. Returns preview with link suggestions

    Equivalent to calling:
    - POST /sources/{source_id}/upload-document
    - POST /sources/{source_id}/extract-from-document

    The user can then review the suggestions and use the save endpoint to commit.

    Supported formats:
    - PDF (.pdf) - Extracts text from all pages
    - Plain text (.txt) - Reads UTF-8 or Latin-1 encoded text

    Limitations:
    - Maximum file size: 10 MB
    - Maximum text length: 50,000 characters (~10-15 pages)
    - Scanned PDFs without OCR will fail

    Requires:
    - LLM service configured (OPENAI_API_KEY)
    - User authentication
    """,
    dependencies=[Depends(require_llm)]
)
async def upload_and_extract(
    source_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentExtractionPreview:
    """Upload document and extract knowledge in one request."""
    user_email = current_user.email if current_user else "system"
    logger.info(
        f"Upload and extract requested for source {source_id} by user {user_email}, "
        f"file: {file.filename}"
    )

    try:
        # Step 1: Extract text from uploaded document
        document_service = DocumentService()
        extraction_result = await document_service.extract_text_from_file(file)

        logger.info(f"Document text extracted: {extraction_result.char_count} chars")

        # Step 2: Store document content in source
        source_service = SourceService(db)
        await source_service.add_document_to_source(
            source_id=source_id,
            document_text=extraction_result.text,
            document_format=extraction_result.format,
            document_file_name=extraction_result.filename,
            user_id=current_user.id if current_user else None
        )

        logger.info("Document content stored in source")

        # Step 3: Extract entities and relations from text
        extraction_service = ExtractionService()
        entities, relations, _ = await extraction_service.extract_batch(
            text=extraction_result.text,
            min_confidence="medium"
        )

        logger.info(f"Extracted {len(entities)} entities and {len(relations)} relations")

        # Step 4: Find entity matches in existing graph
        linking_service = EntityLinkingService(db)
        matches = await linking_service.find_entity_matches(entities)

        # Convert matches to schema format
        link_suggestions = [
            EntityLinkMatch(
                extracted_slug=m.extracted_slug,
                matched_entity_id=m.matched_entity_id,
                matched_entity_slug=m.matched_entity_slug,
                confidence=m.confidence,
                match_type=m.match_type
            )
            for m in matches
        ]

        logger.info(
            f"Entity linking complete: "
            f"{sum(1 for m in matches if m.match_type == 'exact')} exact matches, "
            f"{sum(1 for m in matches if m.match_type == 'synonym')} synonym matches"
        )

        return DocumentExtractionPreview(
            source_id=source_id,
            entities=entities,
            relations=relations,
            entity_count=len(entities),
            relation_count=len(relations),
            link_suggestions=link_suggestions
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload and extract failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload and extract: {str(e)}"
        )


@router.post(
    "/sources/{source_id}/extract-from-url",
    response_model=DocumentExtractionPreview,
    summary="Fetch URL and extract knowledge",
    description="""
    Fetch content from a URL and extract knowledge.

    This endpoint:
    1. Accepts a URL (PubMed article, web page, etc.)
    2. Fetches content using appropriate fetcher (PubMed API for PubMed URLs, web scraping for others)
    3. Stores document content in the source
    4. Extracts entities and relations using LLM
    5. Finds matches in existing knowledge graph
    6. Returns preview with link suggestions

    Supported URL types:
    - PubMed articles (https://pubmed.ncbi.nlm.nih.gov/...)
      - Uses official NCBI E-utilities API
      - Extracts: title, abstract, authors, journal, year, DOI, PMID
    - General web pages (limited support due to anti-bot protection)

    The user can then review the suggestions and use the save endpoint to commit.

    Requires:
    - LLM service configured (OPENAI_API_KEY)
    - User authentication
    """,
    dependencies=[Depends(require_llm)]
)
async def extract_from_url(
    source_id: UUID,
    request: UrlExtractionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentExtractionPreview:
    """Fetch URL content and extract knowledge."""
    user_email = current_user.email if current_user else "system"
    logger.info(
        f"URL extraction requested for source {source_id} by user {user_email}, "
        f"URL: {request.url}"
    )

    try:
        # Step 1: Fetch content from URL
        # Check if it's a PubMed URL
        pubmed_fetcher = PubMedFetcher()
        pmid = pubmed_fetcher.extract_pmid_from_url(request.url)

        if pmid:
            # Use PubMed API
            logger.info(f"Detected PubMed URL, fetching PMID {pmid}")
            article = await pubmed_fetcher.fetch_by_pmid(pmid)
            document_text = article.full_text
            document_filename = f"pubmed_{pmid}.txt"

            # Update source with PubMed metadata
            source_service = SourceService(db)
            from app.schemas.source import SourceWrite
            from sqlalchemy import select
            from app.models.source import Source

            stmt = select(Source).where(Source.id == source_id)
            result = await db.execute(stmt)
            source = result.scalar_one_or_none()

            if source:
                # Update source metadata with PubMed info
                from app.models.source_revision import SourceRevision

                stmt = select(SourceRevision).where(
                    SourceRevision.source_id == source_id,
                    SourceRevision.is_current == True
                )
                result = await db.execute(stmt)
                revision = result.scalar_one_or_none()

                if revision:
                    # Update metadata
                    if not revision.source_metadata:
                        revision.source_metadata = {}
                    revision.source_metadata.update({
                        "pmid": article.pmid,
                        "doi": article.doi,
                        "source": "pubmed"
                    })
                    # Update URL
                    revision.url = article.url
                    # Update authors if not set
                    if not revision.authors and article.authors:
                        revision.authors = article.authors
                    # Update year if not set
                    if not revision.year and article.year:
                        revision.year = article.year
                    # Update origin (journal) if not set
                    if not revision.origin and article.journal:
                        revision.origin = article.journal
                    await db.commit()

            logger.info(f"Fetched PubMed article: {article.title[:60]}... ({len(document_text)} chars)")
        else:
            # Use general URL fetcher
            logger.info("Using general URL fetcher")
            url_fetcher = UrlFetcher()
            fetch_result = await url_fetcher.fetch_url(request.url)
            document_text = fetch_result.text
            document_filename = "web_content.txt"

            logger.info(f"Fetched URL: {fetch_result.title or 'Untitled'} ({len(document_text)} chars)")

        # Step 2: Store document content in source
        source_service = SourceService(db)
        await source_service.add_document_to_source(
            source_id=source_id,
            document_text=document_text,
            document_format="txt",
            document_file_name=document_filename,
            user_id=current_user.id if current_user else None
        )

        logger.info("Document content stored in source")

        # Step 3: Extract entities and relations from text
        extraction_service = ExtractionService()
        entities, relations, _ = await extraction_service.extract_batch(
            text=document_text,
            min_confidence="medium"
        )

        logger.info(f"Extracted {len(entities)} entities and {len(relations)} relations")

        # Step 4: Find entity matches in existing graph
        linking_service = EntityLinkingService(db)
        matches = await linking_service.find_entity_matches(entities)

        # Convert matches to schema format
        link_suggestions = [
            EntityLinkMatch(
                extracted_slug=m.extracted_slug,
                matched_entity_id=m.matched_entity_id,
                matched_entity_slug=m.matched_entity_slug,
                confidence=m.confidence,
                match_type=m.match_type
            )
            for m in matches
        ]

        logger.info(
            f"Entity linking complete: "
            f"{sum(1 for m in matches if m.match_type == 'exact')} exact matches, "
            f"{sum(1 for m in matches if m.match_type == 'synonym')} synonym matches"
        )

        return DocumentExtractionPreview(
            source_id=source_id,
            entities=entities,
            relations=relations,
            entity_count=len(entities),
            relation_count=len(relations),
            link_suggestions=link_suggestions
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL extraction failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract from URL: {str(e)}"
        )
