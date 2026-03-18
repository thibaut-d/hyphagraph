"""
API endpoints for bulk import operations.

Provides a two-step workflow:
1. POST /api/import/entities/preview  — validate rows, return per-row status (no writes)
2. POST /api/import/entities          — execute the import and write to DB

Supported upload formats: CSV (multipart/form-data) and JSON (application/json body).
"""
import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.service_dependencies import get_import_service
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.import_schema import ImportPreviewResult, ImportResult
from app.services.import_service import ImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import", tags=["import"])


def _parse_rows(service: ImportService, file: UploadFile, format: str):
    """Parse uploaded file into EntityImportRow list."""
    content = file.file.read().decode("utf-8")
    if format == "csv":
        return service.parse_csv(content)
    elif format == "json":
        return service.parse_json(content)
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported format: {format!r}. Use 'csv' or 'json'.",
        )


@router.post(
    "/entities/preview",
    response_model=ImportPreviewResult,
    summary="Preview entity import",
)
async def preview_entity_import(
    file: UploadFile = File(..., description="CSV or JSON file"),
    format: str = Form(default="csv", description="'csv' or 'json'"),
    service: ImportService = Depends(get_import_service),
    current_user: User = Depends(get_current_user),
):
    """
    Validate an entity import file and return a per-row preview.

    No data is written to the database. Use this endpoint to show the user
    which rows will be created vs skipped before they confirm the import.
    """
    try:
        rows = _parse_rows(service, file, format)
        return await service.preview_entities(rows)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post(
    "/entities",
    response_model=ImportResult,
    status_code=status.HTTP_201_CREATED,
    summary="Execute entity import",
)
async def import_entities(
    file: UploadFile = File(..., description="CSV or JSON file"),
    format: str = Form(default="csv", description="'csv' or 'json'"),
    service: ImportService = Depends(get_import_service),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a bulk entity import.

    Rows with duplicate slugs are skipped (not an error). Invalid rows
    (missing slug) are counted and returned in `failed`.
    """
    try:
        rows = _parse_rows(service, file, format)
        return await service.import_entities(rows, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
