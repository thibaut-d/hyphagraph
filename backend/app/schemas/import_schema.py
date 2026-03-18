"""Schemas for bulk import endpoints."""
from typing import Literal

from app.schemas.base import Schema


class EntityImportRow(Schema):
    """A single row from a CSV or JSON import file.

    Blank or empty slugs are allowed here; the service handles validation
    and marks those rows as 'invalid' in the preview/import response.
    """

    slug: str = ""
    summary_en: str | None = None
    summary_fr: str | None = None


class EntityImportPreviewRow(Schema):
    """Per-row result shown in the preview stage."""

    row: int
    slug: str
    summary_en: str | None = None
    status: Literal["new", "duplicate", "invalid"]
    error: str | None = None


class ImportPreviewResult(Schema):
    """Response from POST /api/import/entities/preview."""

    rows: list[EntityImportPreviewRow]
    total: int
    new_count: int
    duplicate_count: int
    invalid_count: int


class ImportResult(Schema):
    """Response from POST /api/import/entities (commit)."""

    created: int
    skipped_duplicates: int
    failed: int
    entity_ids: list[str]  # UUIDs as strings
