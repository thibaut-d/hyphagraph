"""Schemas for bulk import endpoints."""
from typing import Literal

from app.schemas.base import Schema
from app.schemas.common_types import JsonObject


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
    summary_fr: str | None = None
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


# =============================================================================
# Source import schemas
# =============================================================================


class SourceImportRow(Schema):
    """A single source parsed from a BibTeX, RIS, or JSON import file."""

    title: str = ""
    kind: str = "article"
    authors: list[str] | None = None
    year: int | None = None
    origin: str | None = None
    url: str = ""
    summary_en: str | None = None
    source_metadata: JsonObject | None = None


class SourceImportPreviewRow(Schema):
    """Per-row result shown in the source import preview stage."""

    row: int
    title: str
    authors_display: str | None = None  # first author et al.
    year: int | None = None
    url: str | None = None
    status: Literal["new", "duplicate", "invalid"]
    error: str | None = None


class SourceImportPreviewResult(Schema):
    """Response from POST /api/import/sources/preview."""

    rows: list[SourceImportPreviewRow]
    total: int
    new_count: int
    duplicate_count: int
    invalid_count: int


class SourceImportResult(Schema):
    """Response from POST /api/import/sources (commit)."""

    created: int
    skipped_duplicates: int
    failed: int
    source_ids: list[str]  # UUIDs as strings
