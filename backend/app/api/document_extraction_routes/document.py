import logging
import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.service_dependencies import get_document_service
from app.api.document_extraction_dependencies import (
    PubMedFetcher,
    raise_internal_api_exception,
    require_llm,
)
from app.database import AsyncSessionLocal
from app.services.url_fetcher import UrlFetcher
from app.api.document_extraction_schemas import UrlExtractionRequest
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.long_running_job import LongRunningJob, LongRunningJobKind
from app.schemas.long_running_job import JobStartResponse
from app.schemas.source import DocumentExtractionPreview, SaveExtractionRequest, SaveExtractionResult
from app.services.document_extraction_processing import (
    build_extraction_preview,
    fetch_document_from_url,
    load_source_document_text,
    save_extraction_to_graph,
    store_document_in_source,
)
from app.services.document_service import DocumentService
from app.services.long_running_job_service import create_job, run_job
from app.llm.base import LLMError
from app.utils.errors import AppException, ErrorCode, SourceNotFoundException, ValidationException


logger = logging.getLogger(__name__)

router = APIRouter(tags=["document-extraction"])


async def _build_url_extraction_preview(
    db: AsyncSession,
    *,
    source_id: UUID,
    url: str,
    user_id: UUID | None,
) -> DocumentExtractionPreview:
    fetched_document = await fetch_document_from_url(
        db,
        source_id=source_id,
        url=url,
        pubmed_fetcher_factory=PubMedFetcher,
        url_fetcher_factory=UrlFetcher,
    )
    await store_document_in_source(
        db,
        source_id=source_id,
        text=fetched_document.text,
        document_format=fetched_document.document_format,
        file_name=fetched_document.file_name,
        user_id=user_id,
        commit=False,
    )
    preview = await build_extraction_preview(
        db,
        source_id=source_id,
        text=fetched_document.text,
        commit=False,
    )
    await db.commit()
    return preview


async def _run_url_extraction_job(job_id: UUID) -> None:
    async with AsyncSessionLocal() as job_db:
        async def operation(db: AsyncSession, job: LongRunningJob) -> DocumentExtractionPreview:
            payload = UrlExtractionRequest.model_validate(job.request_payload)
            if job.source_id is None:
                raise ValueError("URL extraction job is missing source_id")
            return await _build_url_extraction_preview(
                db,
                source_id=job.source_id,
                url=payload.url,
                user_id=job.user_id,
            )

        await run_job(job_db, job_id=job_id, operation=operation)


def _llm_error_to_app_exception(exc: LLMError, context: dict) -> AppException:
    """Convert an LLMError to a structured AppException with a human-readable message."""
    finish_reason = getattr(exc, "finish_reason", None)
    if finish_reason == "length":
        message = "Extraction failed: the document is too long for the current token limit"
        details = "The LLM response was truncated before the JSON output was complete. Try a shorter document or increase max_tokens."
    elif finish_reason == "content_filter":
        message = "Extraction failed: the content was blocked by the LLM safety filter"
        details = "The document or its content triggered the provider's content policy."
    else:
        message = "Extraction failed: LLM did not return a valid response"
        details = str(exc)
    if finish_reason:
        context = {**context, "finish_reason": finish_reason}
    return AppException(
        status_code=503,
        error_code=ErrorCode.LLM_API_ERROR,
        message=message,
        details=details,
        context=context,
    )

@router.post(
    "/sources/{source_id}/extract-from-document",
    response_model=DocumentExtractionPreview,
    summary="Extract knowledge from uploaded document",
    dependencies=[Depends(require_llm)],
)
async def extract_from_document(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentExtractionPreview:
    user_email = current_user.email if current_user else "system"
    logger.info(f"Document extraction requested for source {source_id} by user {user_email}")

    try:
        document_text = await load_source_document_text(db, source_id)
        preview = await build_extraction_preview(db, source_id=source_id, text=document_text)
        logger.info(
            f"Extracted {preview.entity_count} entities and {preview.relation_count} relations from document"
        )
        return preview
    except (AppException, SourceNotFoundException, ValidationException):
        raise
    except LLMError as exc:
        logger.exception("LLM error during document extraction for source %s", source_id)
        raise _llm_error_to_app_exception(exc, {"source_id": str(source_id)}) from exc
    except Exception as exc:
        logger.exception("Document extraction failed for source %s", source_id)
        raise_internal_api_exception(
            message="Failed to extract from document",
            details=str(exc) or type(exc).__name__,
            context={
                "source_id": str(source_id),
                "exception_type": type(exc).__name__,
            },
        )


@router.post(
    "/sources/{source_id}/save-extraction",
    response_model=SaveExtractionResult,
    summary="Save extracted knowledge to graph",
    dependencies=[Depends(require_llm)],
)
async def save_extraction(
    source_id: UUID,
    request: SaveExtractionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SaveExtractionResult:
    logger.info(
        f"Save extraction requested for source {source_id}: "
        f"{len(request.entities_to_create)} new entities, "
        f"{len(request.entity_links)} links, "
        f"{len(request.relations_to_create)} relations"
    )

    try:
        result = await save_extraction_to_graph(
            db,
            source_id=source_id,
            request=request,
            user_id=current_user.id if current_user else None,
        )
        logger.info(
            f"Saved extraction: {len(result.created_entity_ids)} entities "
            f"(created {len(request.entities_to_create)}, linked {len(request.entity_links)}), "
            f"{result.relations_created} relations"
        )
        return result
    except (AppException, SourceNotFoundException, ValidationException):
        raise
    except Exception as exc:
        logger.exception("Save extraction failed for source %s", source_id)
        raise_internal_api_exception(
            message="Failed to save extraction",
            details=str(exc) or type(exc).__name__,
            context={
                "source_id": str(source_id),
                "exception_type": type(exc).__name__,
            },
        )


@router.post(
    "/sources/{source_id}/upload-and-extract",
    response_model=DocumentExtractionPreview,
    summary="Upload document and extract knowledge in one step",
    dependencies=[Depends(require_llm)],
)
async def upload_and_extract(
    source_id: UUID,
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentExtractionPreview:
    user_email = current_user.email if current_user else "system"
    logger.info(
        f"Upload and extract requested for source {source_id} by user {user_email}, "
        f"file: {file.filename}"
    )

    try:
        extraction_result = await document_service.extract_text_from_file(file)
        await store_document_in_source(
            db,
            source_id=source_id,
            text=extraction_result.text,
            document_format=extraction_result.format,
            file_name=extraction_result.filename,
            user_id=current_user.id if current_user else None,
            commit=False,
        )
        preview = await build_extraction_preview(
            db,
            source_id=source_id,
            text=extraction_result.text,
            commit=False,
        )
        await db.commit()
        logger.info(
            f"Extracted {preview.entity_count} entities and {preview.relation_count} relations"
        )
        return preview
    except (AppException, SourceNotFoundException, ValidationException):
        await db.rollback()
        raise
    except LLMError as exc:
        await db.rollback()
        logger.exception("LLM error during upload-and-extract for source %s", source_id)
        raise _llm_error_to_app_exception(exc, {"source_id": str(source_id)}) from exc
    except Exception as exc:
        await db.rollback()
        logger.exception("Upload and extract failed for source %s", source_id)
        raise_internal_api_exception(
            message="Failed to upload and extract",
            details=str(exc) or type(exc).__name__,
            context={
                "source_id": str(source_id),
                "exception_type": type(exc).__name__,
            },
        )


@router.post(
    "/sources/{source_id}/extract-from-url",
    response_model=DocumentExtractionPreview,
    summary="Fetch URL and extract knowledge",
    dependencies=[Depends(require_llm)],
)
async def extract_from_url(
    source_id: UUID,
    request: UrlExtractionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentExtractionPreview:
    user_email = current_user.email if current_user else "system"
    logger.info(
        f"URL extraction requested for source {source_id} by user {user_email}, URL: {request.url}"
    )

    try:
        preview = await _build_url_extraction_preview(
            db,
            source_id=source_id,
            url=request.url,
            user_id=current_user.id if current_user else None,
        )
        logger.info(
            f"Extracted {preview.entity_count} entities and {preview.relation_count} relations"
        )
        return preview
    except (AppException, SourceNotFoundException, ValidationException):
        await db.rollback()
        raise
    except LLMError as exc:
        await db.rollback()
        logger.exception("LLM error during URL extraction for source %s", source_id)
        raise _llm_error_to_app_exception(exc, {"source_id": str(source_id), "url": request.url}) from exc
    except Exception as exc:
        await db.rollback()
        logger.exception("URL extraction failed for source %s", source_id)
        raise_internal_api_exception(
            message="Failed to extract from URL",
            details=str(exc) or type(exc).__name__,
            context={
                "source_id": str(source_id),
                "url": request.url,
                "exception_type": type(exc).__name__,
            },
        )


@router.post(
    "/sources/{source_id}/extract-from-url/jobs",
    response_model=JobStartResponse,
    summary="Start a resumable URL extraction job",
    dependencies=[Depends(require_llm)],
)
async def start_extract_from_url_job(
    source_id: UUID,
    request: UrlExtractionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobStartResponse:
    job = await create_job(
        db,
        kind=LongRunningJobKind.SOURCE_URL_EXTRACTION,
        user_id=current_user.id,
        source_id=source_id,
        request_payload=request.model_dump(mode="json"),
    )
    asyncio.create_task(_run_url_extraction_job(job.id))
    return JobStartResponse(job_id=job.id, status=job.status.value)
