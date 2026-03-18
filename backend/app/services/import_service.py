"""
Import service for bulk entity import from CSV or JSON files.

Supports:
- CSV: columns slug, summary_en, summary_fr (header required)
- JSON: array of objects with same keys

Row limit: 500 rows per request (MVP safeguard).
"""
import csv
import json
import logging
from io import StringIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.schemas.import_schema import (
    EntityImportPreviewRow,
    EntityImportRow,
    ImportPreviewResult,
    ImportResult,
)
from app.utils.revision_helpers import create_new_revision

logger = logging.getLogger(__name__)

MAX_IMPORT_ROWS = 500


class ImportService:
    """Service for bulk entity import from uploaded files."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Parsing
    # -------------------------------------------------------------------------

    def parse_csv(self, content: str) -> list[EntityImportRow]:
        """Parse CSV text into a list of EntityImportRow objects."""
        reader = csv.DictReader(StringIO(content))
        rows: list[EntityImportRow] = []
        for raw in reader:
            slug = (raw.get("slug") or "").strip()
            rows.append(
                EntityImportRow(
                    slug=slug,
                    summary_en=(raw.get("summary_en") or "").strip() or None,
                    summary_fr=(raw.get("summary_fr") or "").strip() or None,
                )
            )
        return rows

    def parse_json(self, content: str) -> list[EntityImportRow]:
        """Parse JSON array text into a list of EntityImportRow objects."""
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("JSON import must be an array of objects")
        rows: list[EntityImportRow] = []
        for item in data:
            slug = str(item.get("slug") or "").strip()
            rows.append(
                EntityImportRow(
                    slug=slug,
                    summary_en=str(item["summary_en"]).strip() or None
                    if item.get("summary_en")
                    else None,
                    summary_fr=str(item["summary_fr"]).strip() or None
                    if item.get("summary_fr")
                    else None,
                )
            )
        return rows

    # -------------------------------------------------------------------------
    # Preview (read-only, no DB writes)
    # -------------------------------------------------------------------------

    async def preview_entities(
        self, rows: list[EntityImportRow]
    ) -> ImportPreviewResult:
        """
        Validate rows and classify each as new, duplicate, or invalid.

        Does NOT write to the database.
        """
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError(
                f"Import exceeds the {MAX_IMPORT_ROWS}-row limit ({len(rows)} rows provided)"
            )

        # Fetch all existing slugs in one query for efficient duplicate detection
        result = await self.db.execute(
            select(EntityRevision.slug).where(EntityRevision.is_current == True)  # noqa: E712
        )
        existing_slugs: set[str] = {r for (r,) in result.all()}

        preview_rows: list[EntityImportPreviewRow] = []
        seen_slugs: set[str] = set()
        new_count = 0
        duplicate_count = 0
        invalid_count = 0

        for i, row in enumerate(rows, start=1):
            slug = row.slug.strip() if row.slug else ""

            if not slug:
                preview_rows.append(
                    EntityImportPreviewRow(
                        row=i,
                        slug="",
                        status="invalid",
                        error="slug is required",
                    )
                )
                invalid_count += 1
                continue

            if slug in existing_slugs or slug in seen_slugs:
                preview_rows.append(
                    EntityImportPreviewRow(
                        row=i,
                        slug=slug,
                        summary_en=row.summary_en,
                        status="duplicate",
                    )
                )
                duplicate_count += 1
            else:
                preview_rows.append(
                    EntityImportPreviewRow(
                        row=i,
                        slug=slug,
                        summary_en=row.summary_en,
                        status="new",
                    )
                )
                new_count += 1
                seen_slugs.add(slug)

        return ImportPreviewResult(
            rows=preview_rows,
            total=len(rows),
            new_count=new_count,
            duplicate_count=duplicate_count,
            invalid_count=invalid_count,
        )

    # -------------------------------------------------------------------------
    # Commit (writes to DB)
    # -------------------------------------------------------------------------

    async def import_entities(
        self,
        rows: list[EntityImportRow],
        user_id: UUID | None = None,
    ) -> ImportResult:
        """
        Import valid rows into the knowledge graph.

        Creates Entity + EntityRevision for each valid new row, per-item error
        handling so a duplicate or DB error in one row doesn't abort the batch.
        """
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError(
                f"Import exceeds the {MAX_IMPORT_ROWS}-row limit ({len(rows)} rows provided)"
            )

        created_ids: list[UUID] = []
        skipped_duplicates = 0
        invalid_count = 0

        for row in rows:
            slug = (row.slug or "").strip()
            if not slug:
                invalid_count += 1
                continue

            summary: dict[str, str] | None = None
            if row.summary_en:
                summary = {"en": row.summary_en}
            if row.summary_fr:
                summary = {**(summary or {}), "fr": row.summary_fr}

            try:
                entity = Entity()
                self.db.add(entity)
                await self.db.flush()

                await create_new_revision(
                    db=self.db,
                    revision_class=EntityRevision,
                    parent_id_field="entity_id",
                    parent_id=entity.id,
                    revision_data={
                        "slug": slug,
                        "summary": summary,
                        "created_by_user_id": user_id,
                    },
                    set_as_current=True,
                )

                created_ids.append(entity.id)

            except IntegrityError as e:
                error_msg = str(e.orig).lower() if e.orig else str(e).lower()
                if (
                    "ix_entity_revisions_slug_current_unique" in error_msg
                    or "unique constraint failed: entity_revisions.slug" in error_msg
                ):
                    skipped_duplicates += 1
                    logger.debug("Skipping duplicate slug on import: %s", slug)
                    await self.db.rollback()
                else:
                    await self.db.rollback()
                    logger.error("IntegrityError importing slug '%s': %s", slug, e, exc_info=True)
                    invalid_count += 1
            except Exception as e:
                await self.db.rollback()
                logger.error("Failed to import slug '%s': %s", slug, e, exc_info=True)
                invalid_count += 1

        await self.db.commit()

        logger.info(
            "Entity import: %d created, %d skipped (duplicates), %d failed/invalid",
            len(created_ids),
            skipped_duplicates,
            invalid_count,
        )

        return ImportResult(
            created=len(created_ids),
            skipped_duplicates=skipped_duplicates,
            failed=invalid_count,
            entity_ids=[str(v) for v in created_ids],
        )
