from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, List
import logging

from app.database import get_db
from app.schemas.source import SourceWrite, SourceRead, DocumentUploadResponse
from app.schemas.filters import SourceFilters, SourceFilterOptions
from app.schemas.pagination import PaginatedResponse
from app.services.source_service import SourceService
from app.services.document_service import DocumentService
from app.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/filter-options", response_model=SourceFilterOptions)
async def get_source_filter_options(
    db: AsyncSession = Depends(get_db),
):
    """
    Get available filter options for sources.

    Returns distinct values for filterable fields without fetching full records.
    Useful for populating filter UI controls efficiently.

    Returns:
        - **kinds**: List of distinct source kinds
        - **year_range**: Minimum and maximum publication years [min, max]
    """
    service = SourceService(db)
    return await service.get_filter_options()

@router.post("/", response_model=SourceRead)
async def create_source(
    payload: SourceWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    service = SourceService(db)
    return await service.create(payload)

@router.get("/", response_model=PaginatedResponse[SourceRead])
async def list_sources(
    kind: Optional[List[str]] = Query(None, description="Filter by source kind"),
    year_min: Optional[int] = Query(None, description="Minimum publication year", ge=1000, le=9999),
    year_max: Optional[int] = Query(None, description="Maximum publication year", ge=1000, le=9999),
    trust_level_min: Optional[float] = Query(None, description="Minimum trust level", ge=0.0, le=1.0),
    trust_level_max: Optional[float] = Query(None, description="Maximum trust level", ge=0.0, le=1.0),
    search: Optional[str] = Query(None, description="Search in title, authors, or origin", max_length=100),
    limit: int = Query(50, description="Maximum number of results", ge=1, le=100),
    offset: int = Query(0, description="Number of results to skip", ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List sources with optional filters and pagination.

    Returns paginated results with total count.

    - **kind**: Filter by kind (multiple values use OR logic)
    - **year_min/year_max**: Filter by publication year range
    - **trust_level_min/trust_level_max**: Filter by trust level range
    - **search**: Case-insensitive search in title, authors, or origin
    - **limit**: Maximum number of results to return (default: 50, max: 100)
    - **offset**: Number of results to skip for pagination (default: 0)
    """
    service = SourceService(db)
    filters = SourceFilters(
        kind=kind,
        year_min=year_min,
        year_max=year_max,
        trust_level_min=trust_level_min,
        trust_level_max=trust_level_max,
        search=search,
        limit=limit,
        offset=offset,
    )
    items, total = await service.list_all(filters=filters)
    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )

@router.get("/{source_id}", response_model=SourceRead)
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    service = SourceService(db)
    return await service.get(source_id)

@router.put("/{source_id}", response_model=SourceRead)
async def update_source(
    source_id: UUID,
    payload: SourceWrite,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    service = SourceService(db)
    return await service.update(source_id, payload, user_id=user.id if user else None)

@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    service = SourceService(db)
    await service.delete(source_id)
    return None


@router.post("/{source_id}/upload-document", response_model=DocumentUploadResponse)
async def upload_document(
    source_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Upload a document (PDF or TXT) to an existing source.

    Extracts text content from the uploaded file and stores it in the source revision
    for future re-extraction and analysis.

    Supported formats:
    - PDF (.pdf) - Extracts text from all pages
    - Plain text (.txt) - Reads UTF-8 or Latin-1 encoded text

    Limitations:
    - Maximum file size: 10 MB
    - Maximum text length: 50,000 characters (~10-15 pages)
    - Scanned PDFs without OCR will fail

    Returns the source ID and a preview of the extracted text.
    """
    logger.info(f"Document upload requested for source {source_id} by user {user.email}")

    # Extract text from document
    document_service = DocumentService()
    extraction_result = await document_service.extract_text_from_file(file)

    # Store document content in source revision
    source_service = SourceService(db)
    await source_service.add_document_to_source(
        source_id=source_id,
        document_text=extraction_result.text,
        document_format=extraction_result.format,
        document_file_name=extraction_result.filename,
        user_id=user.id if user else None
    )

    logger.info(
        f"Document uploaded successfully: {extraction_result.filename} "
        f"({extraction_result.char_count} chars, format: {extraction_result.format})"
    )

    # Return response with preview
    return DocumentUploadResponse(
        source_id=source_id,
        document_text_preview=extraction_result.text[:500],
        document_format=extraction_result.format,
        character_count=extraction_result.char_count,
        truncated=extraction_result.truncated,
        warnings=extraction_result.warnings
    )