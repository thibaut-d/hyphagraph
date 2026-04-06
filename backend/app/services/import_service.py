"""
Import service for bulk entity and source import.

Entity import supports:
- CSV: columns slug, summary_en, summary_fr (header required)
- JSON: array of objects with same keys

Source import supports:
- BibTeX (.bib)
- RIS (.ris)
- JSON: array of objects with keys matching SourceImportRow fields

Row limit: 500 rows per request (MVP safeguard).
"""
import csv
import json
import logging
import re
from io import StringIO
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.models.ui_category import UiCategory
from app.schemas.entity_term import EntityTermWrite
from app.schemas.import_schema import (
    EntityImportPreviewRow,
    EntityImportRow,
    ImportPreviewResult,
    ImportResult,
    SourceImportPreviewResult,
    SourceImportPreviewRow,
    SourceImportResult,
    SourceImportRow,
)
from app.services.entity_term_service import EntityTermService
from app.utils.revision_helpers import create_new_revision

logger = logging.getLogger(__name__)

MAX_IMPORT_ROWS = 500

# Same pattern as EntityWrite.slug — enforced here so invalid slugs are
# rejected at preview time rather than silently stored via the ORM path.
_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")

# ---------------------------------------------------------------------------
# BibTeX entry-type → SourceRevision kind mapping
# ---------------------------------------------------------------------------

_BIBTEX_KIND_MAP: dict[str, str] = {
    "article": "article",
    "book": "book",
    "inbook": "book",
    "incollection": "book",
    "inproceedings": "conference_paper",
    "proceedings": "conference_paper",
    "conference": "conference_paper",
    "techreport": "report",
    "report": "report",
    "phdthesis": "thesis",
    "mastersthesis": "thesis",
    "thesis": "thesis",
    "misc": "article",
    "unpublished": "article",
    "manual": "report",
    "booklet": "book",
    "online": "website",
    "electronic": "website",
    "www": "website",
}

# ---------------------------------------------------------------------------
# RIS type → SourceRevision kind mapping
# ---------------------------------------------------------------------------

_RIS_KIND_MAP: dict[str, str] = {
    "JOUR": "article",
    "JFULL": "article",
    "ABST": "article",
    "BOOK": "book",
    "CHAP": "book",
    "CONF": "conference_paper",
    "CPAPER": "conference_paper",
    "RPRT": "report",
    "THES": "thesis",
    "WEB": "website",
    "ELEC": "website",
    "GEN": "article",
    "MGZN": "article",
    "NEWS": "article",
    "CASE": "case_report",
}


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
                    ui_category_slug=(raw.get("ui_category_slug") or "").strip() or None,
                    display_name=(raw.get("display_name") or "").strip() or None,
                    display_name_en=(raw.get("display_name_en") or "").strip() or None,
                    display_name_fr=(raw.get("display_name_fr") or "").strip() or None,
                    summary_en=(raw.get("summary_en") or "").strip() or None,
                    summary_fr=(raw.get("summary_fr") or "").strip() or None,
                    aliases=(raw.get("aliases") or "").strip() or None,
                )
            )
        return rows

    def parse_json(self, content: str) -> list[EntityImportRow]:
        """Parse JSON array text into a list of EntityImportRow objects."""
        data = json.loads(content)
        # Unwrap export envelope: {"export_type": "entities", "entities": [...]}
        if isinstance(data, dict) and isinstance(data.get("entities"), list):
            data = data["entities"]
        if not isinstance(data, list):
            raise ValueError("JSON import must be an array of objects")
        rows: list[EntityImportRow] = []
        for item in data:
            slug = str(item.get("slug") or "").strip()
            # aliases: accept either a semicolon string or an array of {term, language} objects
            aliases_raw = item.get("aliases")
            if isinstance(aliases_raw, list):
                parts = []
                for a in aliases_raw:
                    if isinstance(a, dict):
                        term = str(a.get("term") or "").strip()
                        lang = str(a.get("language") or "").strip()
                        if term:
                            parts.append(f"{term}:{lang}")
                aliases_str = ";".join(parts) or None
            else:
                aliases_str = str(aliases_raw).strip() or None if aliases_raw else None
            rows.append(
                EntityImportRow(
                    slug=slug,
                    ui_category_slug=str(item.get("ui_category_slug") or "").strip() or None,
                    display_name=str(item.get("display_name") or "").strip() or None,
                    display_name_en=str(item.get("display_name_en") or "").strip() or None,
                    display_name_fr=str(item.get("display_name_fr") or "").strip() or None,
                    summary_en=str(item["summary_en"]).strip() or None if item.get("summary_en") else None,
                    summary_fr=str(item["summary_fr"]).strip() or None if item.get("summary_fr") else None,
                    aliases=aliases_str,
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
            display_name = row.display_name_en or row.display_name or row.display_name_fr

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

            if not _SLUG_RE.match(slug):
                preview_rows.append(
                    EntityImportPreviewRow(
                        row=i,
                        slug=slug,
                        status="invalid",
                        error="slug must match ^[a-z][a-z0-9-]*$ (lowercase, start with letter, hyphens only)",
                    )
                )
                invalid_count += 1
                continue

            if slug in existing_slugs or slug in seen_slugs:
                preview_rows.append(
                    EntityImportPreviewRow(
                        row=i,
                        slug=slug,
                        display_name=display_name,
                        ui_category_slug=row.ui_category_slug,
                        summary_en=row.summary_en,
                        summary_fr=row.summary_fr,
                        status="duplicate",
                    )
                )
                duplicate_count += 1
            else:
                preview_rows.append(
                    EntityImportPreviewRow(
                        row=i,
                        slug=slug,
                        display_name=display_name,
                        ui_category_slug=row.ui_category_slug,
                        summary_en=row.summary_en,
                        summary_fr=row.summary_fr,
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

    @staticmethod
    def _parse_aliases(aliases_str: str | None) -> list[tuple[str, str | None]]:
        """Parse semicolon-separated 'term:lang' pairs into (term, language) tuples.

        Language is None for international (empty or missing after colon).
        Examples:
            "ASA:en;AAS:fr;aspirin:" → [("ASA","en"), ("AAS","fr"), ("aspirin", None)]
            "aspirin"               → [("aspirin", None)]
        """
        if not aliases_str:
            return []
        result = []
        for part in aliases_str.split(";"):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                term, _, lang = part.rpartition(":")
                term = term.strip()
                lang = lang.strip() or None
            else:
                term = part
                lang = None
            if term:
                result.append((term, lang))
        return result

    async def import_entities(
        self,
        rows: list[EntityImportRow],
        user_id: UUID | None = None,
    ) -> ImportResult:
        """
        Import valid rows into the knowledge graph.

        Creates Entity + EntityRevision for each valid new row, per-item error
        handling so a duplicate or DB error in one row doesn't abort the batch.
        Also creates entity terms (display names + aliases) when provided.
        """
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError(
                f"Import exceeds the {MAX_IMPORT_ROWS}-row limit ({len(rows)} rows provided)"
            )

        # Pre-fetch all UiCategory slugs → UUID map in one query
        cat_result = await self.db.execute(select(UiCategory.slug, UiCategory.id))
        category_map: dict[str, UUID] = {slug: id_ for slug, id_ in cat_result.all()}

        created_ids: list[UUID] = []
        skipped_duplicates = 0
        invalid_count = 0

        term_service = EntityTermService(self.db)

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

            ui_category_id = category_map.get(row.ui_category_slug) if row.ui_category_slug else None

            try:
                async with self.db.begin_nested():
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
                            "ui_category_id": ui_category_id,
                            "created_by_user_id": user_id,
                        },
                        set_as_current=True,
                    )

                # Only reached if the savepoint committed successfully
                created_ids.append(entity.id)

                # Build entity terms from display names + aliases
                terms: list[EntityTermWrite] = []
                order = 0
                for lang, value in [
                    (None, row.display_name),
                    ("en", row.display_name_en),
                    ("fr", row.display_name_fr),
                ]:
                    if value and value.strip():
                        terms.append(EntityTermWrite(
                            term=value.strip(),
                            language=lang,
                            display_order=order,
                            is_display_name=True,
                        ))
                        order += 1

                for term_text, lang in self._parse_aliases(row.aliases):
                    # Skip alias if it duplicates a display name
                    if not any(t.term == term_text and t.language == lang for t in terms):
                        terms.append(EntityTermWrite(
                            term=term_text,
                            language=lang,
                            display_order=order,
                            is_display_name=False,
                        ))
                        order += 1

                if terms:
                    await term_service.bulk_update(entity.id, terms)

            except IntegrityError as e:
                # Savepoint already rolled back; outer transaction is intact
                error_msg = str(e.orig).lower() if e.orig else str(e).lower()
                if (
                    "ix_entity_revisions_slug_current_unique" in error_msg
                    or "unique constraint failed: entity_revisions.slug" in error_msg
                ):
                    skipped_duplicates += 1
                    logger.debug("Skipping duplicate slug on import: %s", slug)
                else:
                    logger.error("IntegrityError importing slug '%s': %s", slug, e, exc_info=True)
                    invalid_count += 1
            except Exception as e:
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

    # =========================================================================
    # Source import
    # =========================================================================

    # -------------------------------------------------------------------------
    # Source parsers
    # -------------------------------------------------------------------------

    def parse_bibtex(self, content: str) -> list[SourceImportRow]:
        """Parse BibTeX text into a list of SourceImportRow objects."""
        rows: list[SourceImportRow] = []

        # Find all @type{key, ...} entries (handle nested braces).
        # [^,\n]* restricts the citation-key to the same line so that
        # @string/@preamble entries without a comma don't greedily consume
        # the comma from the next real entry.
        entry_pattern = re.compile(
            r"@\s*(\w+)\s*\{[^,\n]*,", re.IGNORECASE
        )
        # Split the content at each entry boundary
        for match in entry_pattern.finditer(content):
            entry_type = match.group(1).lower()
            if entry_type in ("string", "preamble", "comment"):
                continue

            start = match.end()
            # Walk forward to find the matching closing brace
            depth = 1
            pos = start
            while pos < len(content) and depth > 0:
                if content[pos] == "{":
                    depth += 1
                elif content[pos] == "}":
                    depth -= 1
                pos += 1
            entry_body = content[start : pos - 1]

            rows.append(self._parse_bibtex_entry(entry_type, entry_body))

        return rows

    @staticmethod
    def _extract_bibtex_field(body: str, field: str) -> str | None:
        """Extract a single field value from a BibTeX entry body."""
        pattern = re.compile(
            r"\b" + re.escape(field) + r"\s*=\s*"
            r"(?:\{((?:[^{}]|\{[^{}]*\})*)\}"  # {value} (one level of nesting)
            r'|"([^"]*)"'  # "value"
            r"|(\d+))",  # bare number
            re.IGNORECASE | re.DOTALL,
        )
        m = pattern.search(body)
        if not m:
            return None
        value = m.group(1) or m.group(2) or m.group(3) or ""
        # Strip inner braces used for case protection: {A}spirin → Aspirin
        value = re.sub(r"\{([^{}]*)\}", r"\1", value)
        return value.strip() or None

    def _parse_bibtex_entry(self, entry_type: str, body: str) -> SourceImportRow:
        """Convert one BibTeX entry body into a SourceImportRow."""
        title = self._extract_bibtex_field(body, "title") or ""

        # Authors: split by " and " (BibTeX convention)
        author_raw = self._extract_bibtex_field(body, "author")
        authors: list[str] | None = None
        if author_raw:
            authors = [a.strip() for a in re.split(r"\s+and\s+", author_raw) if a.strip()]

        year_raw = self._extract_bibtex_field(body, "year")
        year: int | None = None
        if year_raw:
            try:
                year = int(year_raw[:4])
            except (ValueError, TypeError):
                pass

        # Origin: prefer journal > booktitle > publisher > school > institution
        origin = (
            self._extract_bibtex_field(body, "journal")
            or self._extract_bibtex_field(body, "booktitle")
            or self._extract_bibtex_field(body, "publisher")
            or self._extract_bibtex_field(body, "school")
            or self._extract_bibtex_field(body, "institution")
        )

        url = self._extract_bibtex_field(body, "url") or ""
        doi = self._extract_bibtex_field(body, "doi")

        # Build URL from DOI if no explicit URL
        if not url and doi:
            url = f"https://doi.org/{doi}"

        abstract = self._extract_bibtex_field(body, "abstract")

        metadata: dict[str, object] = {}
        if doi:
            metadata["doi"] = doi
        pmid = self._extract_bibtex_field(body, "pmid") or self._extract_bibtex_field(body, "pubmedid")
        if pmid:
            metadata["pmid"] = pmid

        kind = _BIBTEX_KIND_MAP.get(entry_type, "article")

        return SourceImportRow(
            title=title,
            kind=kind,
            authors=authors or None,
            year=year,
            origin=origin,
            url=url,
            summary_en=abstract,
            source_metadata=metadata if metadata else None,
        )

    def parse_ris(self, content: str) -> list[SourceImportRow]:
        """Parse RIS text into a list of SourceImportRow objects."""
        rows: list[SourceImportRow] = []

        # RIS lines: "TAG  - value" — trailing space is optional (ER  - has none)
        tag_pattern = re.compile(r"^([A-Z0-9]{2})  - ?(.*)$")

        current: dict[str, list[str]] = {}

        def _flush(rec: dict[str, list[str]]) -> None:
            if rec:
                rows.append(self._parse_ris_record(rec))

        for raw_line in content.splitlines():
            line = raw_line.rstrip()
            m = tag_pattern.match(line)
            if m:
                tag, value = m.group(1), m.group(2).strip()
                if tag == "ER":
                    _flush(current)
                    current = {}
                else:
                    current.setdefault(tag, []).append(value)
            # else: continuation line (rare in practice) — ignore

        _flush(current)  # catch entries without ER terminator
        return rows

    def _parse_ris_record(self, rec: dict[str, list[str]]) -> SourceImportRow:
        """Convert one RIS record dict into a SourceImportRow."""
        def first(tags: list[str]) -> str | None:
            for tag in tags:
                vals = rec.get(tag)
                if vals:
                    return vals[0].strip() or None
            return None

        ty = first(["TY"]) or "GEN"
        kind = _RIS_KIND_MAP.get(ty, "article")

        title = first(["TI", "T1", "CT"]) or ""

        # Authors from AU, A1, A2, A3 (each line is one author)
        author_vals: list[str] = []
        for tag in ["AU", "A1", "A2", "A3"]:
            author_vals.extend(rec.get(tag, []))
        authors = [a.strip() for a in author_vals if a.strip()] or None

        # Year from PY or Y1 (may be "2023/01/01/" or just "2023")
        year: int | None = None
        py_raw = first(["PY", "Y1", "DA"])
        if py_raw:
            yr_match = re.match(r"(\d{4})", py_raw)
            if yr_match:
                year = int(yr_match.group(1))

        origin = first(["JO", "JF", "T2", "BT", "PB", "J2"])
        url = first(["UR", "LK", "L1", "L2"]) or ""
        doi = first(["DO"])

        if not url and doi:
            url = f"https://doi.org/{doi}"

        abstract = first(["AB", "N2"])

        metadata: dict[str, object] = {}
        if doi:
            metadata["doi"] = doi
        pmid = first(["PM", "AN"])
        if pmid:
            metadata["pmid"] = pmid

        return SourceImportRow(
            title=title,
            kind=kind,
            authors=authors,
            year=year,
            origin=origin,
            url=url,
            summary_en=abstract,
            source_metadata=metadata if metadata else None,
        )

    def parse_sources_json(self, content: str) -> list[SourceImportRow]:
        """Parse a JSON array of source objects into SourceImportRow list."""
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("JSON import must be an array of objects")
        rows: list[SourceImportRow] = []
        for item in data:
            if not isinstance(item, dict):
                rows.append(SourceImportRow())
                continue
            authors_raw = item.get("authors")
            if isinstance(authors_raw, str):
                authors_raw = [a.strip() for a in authors_raw.split(";") if a.strip()] or None
            year_raw = item.get("year")
            year: int | None = None
            if year_raw is not None:
                try:
                    year = int(year_raw)
                except (TypeError, ValueError):
                    pass
            rows.append(
                SourceImportRow(
                    title=str(item.get("title") or "").strip(),
                    kind=str(item.get("kind") or "article").strip() or "article",
                    authors=authors_raw,
                    year=year,
                    origin=str(item.get("origin") or "").strip() or None,
                    url=str(item.get("url") or "").strip(),
                    summary_en=str(item.get("summary_en") or "").strip() or None,
                    source_metadata=item.get("source_metadata"),
                )
            )
        return rows

    # -------------------------------------------------------------------------
    # Source preview (read-only, no DB writes)
    # -------------------------------------------------------------------------

    @staticmethod
    def _authors_display(authors: list[str] | None) -> str | None:
        if not authors:
            return None
        if len(authors) == 1:
            return authors[0]
        return f"{authors[0]} et al."

    async def preview_sources(
        self, rows: list[SourceImportRow]
    ) -> SourceImportPreviewResult:
        """Validate rows and classify each as new, duplicate, or invalid.

        Duplicate detection:
        - If URL is non-empty: match against existing source revision URLs.
        - If URL is empty: match against existing titles (case-insensitive).

        Does NOT write to the database.
        """
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError(
                f"Import exceeds the {MAX_IMPORT_ROWS}-row limit ({len(rows)} rows provided)"
            )

        # Fetch existing URLs and normalised titles in one pass
        result = await self.db.execute(
            select(SourceRevision.url, SourceRevision.title).where(
                SourceRevision.is_current == True  # noqa: E712
            )
        )
        existing_urls: set[str] = set()
        existing_titles: set[str] = set()
        for url, title in result.all():
            if url:
                existing_urls.add(url.strip())
            if title:
                existing_titles.add(title.strip().lower())

        preview_rows: list[SourceImportPreviewRow] = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        new_count = 0
        duplicate_count = 0
        invalid_count = 0

        for i, row in enumerate(rows, start=1):
            title = (row.title or "").strip()

            if not title:
                preview_rows.append(
                    SourceImportPreviewRow(
                        row=i,
                        title="",
                        status="invalid",
                        error="title is required",
                    )
                )
                invalid_count += 1
                continue

            url = (row.url or "").strip()
            title_lower = title.lower()

            # Determine duplicate
            is_duplicate = False
            if url:
                if url in existing_urls or url in seen_urls:
                    is_duplicate = True
            else:
                if title_lower in existing_titles or title_lower in seen_titles:
                    is_duplicate = True

            if is_duplicate:
                preview_rows.append(
                    SourceImportPreviewRow(
                        row=i,
                        title=title,
                        authors_display=self._authors_display(row.authors),
                        year=row.year,
                        url=url or None,
                        status="duplicate",
                    )
                )
                duplicate_count += 1
            else:
                preview_rows.append(
                    SourceImportPreviewRow(
                        row=i,
                        title=title,
                        authors_display=self._authors_display(row.authors),
                        year=row.year,
                        url=url or None,
                        status="new",
                    )
                )
                new_count += 1
                if url:
                    seen_urls.add(url)
                seen_titles.add(title_lower)

        return SourceImportPreviewResult(
            rows=preview_rows,
            total=len(rows),
            new_count=new_count,
            duplicate_count=duplicate_count,
            invalid_count=invalid_count,
        )

    # -------------------------------------------------------------------------
    # Source commit (writes to DB)
    # -------------------------------------------------------------------------

    async def import_sources(
        self,
        rows: list[SourceImportRow],
        user_id: UUID | None = None,
    ) -> SourceImportResult:
        """Import valid rows as Sources + SourceRevisions.

        Duplicates (matched by URL or title) are skipped, not errored.
        """
        if len(rows) > MAX_IMPORT_ROWS:
            raise ValueError(
                f"Import exceeds the {MAX_IMPORT_ROWS}-row limit ({len(rows)} rows provided)"
            )

        # Fetch existing URLs + titles for duplicate detection
        result = await self.db.execute(
            select(SourceRevision.url, SourceRevision.title).where(
                SourceRevision.is_current == True  # noqa: E712
            )
        )
        existing_urls: set[str] = set()
        existing_titles: set[str] = set()
        for url, title in result.all():
            if url:
                existing_urls.add(url.strip())
            if title:
                existing_titles.add(title.strip().lower())

        created_ids: list[UUID] = []
        skipped_duplicates = 0
        invalid_count = 0
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()

        for row in rows:
            title = (row.title or "").strip()
            if not title:
                invalid_count += 1
                continue

            url = (row.url or "").strip()
            title_lower = title.lower()

            # Duplicate check
            is_duplicate = False
            if url:
                if url in existing_urls or url in seen_urls:
                    is_duplicate = True
            else:
                if title_lower in existing_titles or title_lower in seen_titles:
                    is_duplicate = True

            if is_duplicate:
                skipped_duplicates += 1
                continue

            # Build summary dict
            summary: dict[str, str] | None = None
            if row.summary_en:
                summary = {"en": row.summary_en}

            try:
                async with self.db.begin_nested():
                    source = Source()
                    self.db.add(source)
                    await self.db.flush()

                    await create_new_revision(
                        db=self.db,
                        revision_class=SourceRevision,
                        parent_id_field="source_id",
                        parent_id=source.id,
                        revision_data={
                            "title": title,
                            "kind": row.kind or "article",
                            "authors": row.authors,
                            "year": row.year,
                            "origin": row.origin,
                            "url": url,
                            "summary": summary,
                            "trust_level": row.trust_level,
                            "source_metadata": row.source_metadata,
                            "created_by_user_id": user_id,
                        },
                        set_as_current=True,
                    )

                # Only reached if the savepoint committed successfully
                created_ids.append(source.id)

                # Track for within-batch duplicate detection
                if url:
                    seen_urls.add(url)
                seen_titles.add(title_lower)
                if url:
                    existing_urls.add(url)
                existing_titles.add(title_lower)

            except IntegrityError as e:
                # Savepoint already rolled back; outer transaction is intact
                logger.error("IntegrityError importing source '%s': %s", title, e, exc_info=True)
                invalid_count += 1
            except Exception as e:
                logger.error("Failed to import source '%s': %s", title, e, exc_info=True)
                invalid_count += 1

        await self.db.commit()

        logger.info(
            "Source import: %d created, %d skipped (duplicates), %d failed/invalid",
            len(created_ids),
            skipped_duplicates,
            invalid_count,
        )

        return SourceImportResult(
            created=len(created_ids),
            skipped_duplicates=skipped_duplicates,
            failed=invalid_count,
            source_ids=[str(v) for v in created_ids],
        )
