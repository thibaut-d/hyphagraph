"""
Tests for ImportService.

Tests cover:
- CSV/JSON parsing
- Preview: duplicate detection, invalid row handling
- Import execution: creates entities, skips duplicates, reports failures
- Row limit enforcement
"""

import pytest

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.user import User
from app.services.import_service import ImportService, MAX_IMPORT_ROWS
from app.schemas.import_schema import EntityImportRow


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service(db_session):
    return ImportService(db_session)


@pytest.fixture
async def existing_entity(db_session):
    """Create a pre-existing entity with slug 'aspirin'."""
    user = User(
        email="seeder@example.com",
        hashed_password="x",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    entity = Entity()
    db_session.add(entity)
    await db_session.flush()

    rev = EntityRevision(
        entity_id=entity.id,
        slug="aspirin",
        is_current=True,
        created_by_user_id=user.id,
    )
    db_session.add(rev)
    await db_session.commit()
    return entity


# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------


def test_parse_csv_basic(service):
    csv_text = "slug,summary_en,summary_fr\naspirin,A drug,Un médicament\nibuprofen,,\n"
    rows = service.parse_csv(csv_text)
    assert len(rows) == 2
    assert rows[0].slug == "aspirin"
    assert rows[0].summary_en == "A drug"
    assert rows[0].summary_fr == "Un médicament"
    assert rows[1].slug == "ibuprofen"
    assert rows[1].summary_en is None


def test_parse_csv_handles_whitespace(service):
    csv_text = "slug,summary_en\n  aspirin  , A drug \n"
    rows = service.parse_csv(csv_text)
    assert rows[0].slug == "aspirin"
    assert rows[0].summary_en == "A drug"


def test_parse_json_basic(service):
    import json
    data = [{"slug": "aspirin", "summary_en": "A drug"}, {"slug": "ibuprofen"}]
    rows = service.parse_json(json.dumps(data))
    assert len(rows) == 2
    assert rows[0].slug == "aspirin"
    assert rows[1].slug == "ibuprofen"


def test_parse_json_not_array_raises(service):
    with pytest.raises(ValueError, match="array"):
        service.parse_json('{"slug": "aspirin"}')


# ---------------------------------------------------------------------------
# Preview tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preview_new_rows(service):
    rows = [
        EntityImportRow(slug="caffeine", summary_en="A stimulant"),
        EntityImportRow(slug="melatonin"),
    ]
    result = await service.preview_entities(rows)
    assert result.new_count == 2
    assert result.duplicate_count == 0
    assert result.invalid_count == 0
    assert result.rows[0].status == "new"
    assert result.rows[1].status == "new"


@pytest.mark.asyncio
async def test_preview_detects_existing_slug(service, existing_entity):
    rows = [EntityImportRow(slug="aspirin")]
    result = await service.preview_entities(rows)
    assert result.duplicate_count == 1
    assert result.rows[0].status == "duplicate"


@pytest.mark.asyncio
async def test_preview_detects_within_file_duplicate(service):
    rows = [
        EntityImportRow(slug="caffeine"),
        EntityImportRow(slug="caffeine"),
    ]
    result = await service.preview_entities(rows)
    # First occurrence is "new", second is "duplicate"
    assert result.new_count == 1
    assert result.duplicate_count == 1


@pytest.mark.asyncio
async def test_preview_invalid_empty_slug(service):
    rows = [EntityImportRow(slug="valid"), EntityImportRow(slug="  ")]
    result = await service.preview_entities(rows)
    assert result.new_count == 1
    assert result.invalid_count == 1
    assert result.rows[1].status == "invalid"
    assert result.rows[1].error is not None


@pytest.mark.asyncio
async def test_preview_row_limit_enforced(service):
    rows = [EntityImportRow(slug=f"entity-{i}") for i in range(MAX_IMPORT_ROWS + 1)]
    with pytest.raises(ValueError, match="row limit"):
        await service.preview_entities(rows)


# ---------------------------------------------------------------------------
# Import execution tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_creates_entities(service, db_session):
    rows = [
        EntityImportRow(slug="caffeine", summary_en="A stimulant"),
        EntityImportRow(slug="melatonin"),
    ]
    result = await service.import_entities(rows)
    assert result.created == 2
    assert result.skipped_duplicates == 0
    assert result.failed == 0
    assert len(result.entity_ids) == 2

    # Verify in DB
    from sqlalchemy import select
    revisions = (await db_session.execute(
        select(EntityRevision).where(EntityRevision.slug.in_(["caffeine", "melatonin"]))
    )).scalars().all()
    assert len(revisions) == 2


@pytest.mark.asyncio
async def test_import_skips_existing_slug(service, existing_entity):
    rows = [EntityImportRow(slug="aspirin")]
    result = await service.import_entities(rows)
    assert result.created == 0
    assert result.skipped_duplicates == 1


@pytest.mark.asyncio
async def test_import_skips_invalid_rows(service):
    rows = [
        EntityImportRow(slug="valid-entity"),
        EntityImportRow(slug="  "),  # blank slug → invalid
    ]
    result = await service.import_entities(rows)
    assert result.created == 1
    assert result.failed == 1


@pytest.mark.asyncio
async def test_import_row_limit_enforced(service):
    rows = [EntityImportRow(slug=f"entity-{i}") for i in range(MAX_IMPORT_ROWS + 1)]
    with pytest.raises(ValueError, match="row limit"):
        await service.import_entities(rows)


# ===========================================================================
# Source import tests
# ===========================================================================

from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.schemas.import_schema import SourceImportRow


# ---------------------------------------------------------------------------
# Source fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def existing_source(db_session):
    """Create a pre-existing source with known URL and title."""
    user = User(
        email="sourceseeder@example.com",
        hashed_password="x",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    src = Source()
    db_session.add(src)
    await db_session.flush()

    rev = SourceRevision(
        source_id=src.id,
        kind="article",
        title="Aspirin in cardiology",
        url="https://doi.org/10.1234/aspirin",
        is_current=True,
        created_by_user_id=user.id,
    )
    db_session.add(rev)
    await db_session.commit()
    return src


# ---------------------------------------------------------------------------
# BibTeX parser tests
# ---------------------------------------------------------------------------


def test_parse_bibtex_article(service):
    bib = """\
@article{smith2020,
  title  = {Aspirin in cardiology},
  author = {Smith, John and Doe, Jane},
  year   = {2020},
  journal = {Cardiology Today},
  url    = {https://example.com/aspirin},
  abstract = {A review of aspirin use.},
  doi    = {10.1234/aspirin},
}
"""
    rows = service.parse_bibtex(bib)
    assert len(rows) == 1
    r = rows[0]
    assert r.title == "Aspirin in cardiology"
    assert r.kind == "article"
    assert r.authors == ["Smith, John", "Doe, Jane"]
    assert r.year == 2020
    assert r.origin == "Cardiology Today"
    assert r.url == "https://example.com/aspirin"
    assert r.summary_en == "A review of aspirin use."
    assert r.source_metadata is not None
    assert r.source_metadata["doi"] == "10.1234/aspirin"


def test_parse_bibtex_doi_url_fallback(service):
    bib = """\
@article{jones2021,
  title = {Ibuprofen study},
  doi   = {10.9999/ibuprofen},
}
"""
    rows = service.parse_bibtex(bib)
    assert rows[0].url == "https://doi.org/10.9999/ibuprofen"


def test_parse_bibtex_multiple_entries(service):
    bib = """\
@article{a2020, title={First}, year={2020}}
@book{b2021, title={Second}, year={2021}}
"""
    rows = service.parse_bibtex(bib)
    assert len(rows) == 2
    assert rows[0].kind == "article"
    assert rows[1].kind == "book"


def test_parse_bibtex_skips_string_preamble(service):
    bib = """\
@string{JCAR = "J. Cardiol."}
@preamble{"This is a preamble"}
@article{x2022, title={Real entry}}
"""
    rows = service.parse_bibtex(bib)
    assert len(rows) == 1
    assert rows[0].title == "Real entry"


def test_parse_bibtex_inproceedings_kind(service):
    bib = '@inproceedings{conf2020, title={Conference paper}}'
    rows = service.parse_bibtex(bib)
    assert rows[0].kind == "conference_paper"


# ---------------------------------------------------------------------------
# RIS parser tests
# ---------------------------------------------------------------------------


def test_parse_ris_basic(service):
    ris = """\
TY  - JOUR
TI  - Aspirin in cardiology
AU  - Smith, John
AU  - Doe, Jane
PY  - 2020
JO  - Cardiology Today
UR  - https://example.com/aspirin
AB  - A review of aspirin use.
DO  - 10.1234/aspirin
ER  -
"""
    rows = service.parse_ris(ris)
    assert len(rows) == 1
    r = rows[0]
    assert r.title == "Aspirin in cardiology"
    assert r.kind == "article"
    assert r.authors == ["Smith, John", "Doe, Jane"]
    assert r.year == 2020
    assert r.origin == "Cardiology Today"
    assert r.url == "https://example.com/aspirin"
    assert r.summary_en == "A review of aspirin use."
    assert r.source_metadata["doi"] == "10.1234/aspirin"


def test_parse_ris_doi_url_fallback(service):
    ris = "TY  - JOUR\nTI  - X\nDO  - 10.9999/x\nER  -\n"
    rows = service.parse_ris(ris)
    assert rows[0].url == "https://doi.org/10.9999/x"


def test_parse_ris_multiple_records(service):
    ris = """\
TY  - JOUR
TI  - First article
ER  -
TY  - BOOK
TI  - A book
ER  -
"""
    rows = service.parse_ris(ris)
    assert len(rows) == 2
    assert rows[0].kind == "article"
    assert rows[1].kind == "book"


def test_parse_ris_year_partial(service):
    ris = "TY  - JOUR\nTI  - X\nPY  - 2021/01/15\nER  -\n"
    rows = service.parse_ris(ris)
    assert rows[0].year == 2021


# ---------------------------------------------------------------------------
# Source JSON parser tests
# ---------------------------------------------------------------------------


def test_parse_sources_json_basic(service):
    import json
    data = [
        {"title": "Aspirin study", "kind": "article", "year": 2020, "url": "https://example.com"},
        {"title": "Ibuprofen study"},
    ]
    rows = service.parse_sources_json(json.dumps(data))
    assert len(rows) == 2
    assert rows[0].title == "Aspirin study"
    assert rows[0].year == 2020
    assert rows[1].title == "Ibuprofen study"
    assert rows[1].kind == "article"  # default


def test_parse_sources_json_not_array_raises(service):
    with pytest.raises(ValueError, match="array"):
        service.parse_sources_json('{"title": "x"}')


def test_parse_sources_json_string_authors(service):
    import json
    data = [{"title": "X", "authors": "Smith, J; Doe, J"}]
    rows = service.parse_sources_json(json.dumps(data))
    assert rows[0].authors == ["Smith, J", "Doe, J"]


# ---------------------------------------------------------------------------
# Source preview tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preview_sources_new_rows(service):
    rows = [
        SourceImportRow(title="Novel drug A", url="https://example.com/a"),
        SourceImportRow(title="Novel drug B", url="https://example.com/b"),
    ]
    result = await service.preview_sources(rows)
    assert result.new_count == 2
    assert result.duplicate_count == 0
    assert result.invalid_count == 0
    assert result.rows[0].status == "new"


@pytest.mark.asyncio
async def test_preview_sources_detects_existing_url(service, existing_source):
    rows = [SourceImportRow(title="Duplicate", url="https://doi.org/10.1234/aspirin")]
    result = await service.preview_sources(rows)
    assert result.duplicate_count == 1
    assert result.rows[0].status == "duplicate"


@pytest.mark.asyncio
async def test_preview_sources_detects_existing_title_no_url(service, existing_source):
    rows = [SourceImportRow(title="Aspirin in cardiology", url="")]
    result = await service.preview_sources(rows)
    assert result.duplicate_count == 1
    assert result.rows[0].status == "duplicate"


@pytest.mark.asyncio
async def test_preview_sources_invalid_missing_title(service):
    rows = [SourceImportRow(title="", url="https://example.com")]
    result = await service.preview_sources(rows)
    assert result.invalid_count == 1
    assert result.rows[0].status == "invalid"
    assert result.rows[0].error is not None


@pytest.mark.asyncio
async def test_preview_sources_within_batch_url_dedup(service):
    rows = [
        SourceImportRow(title="A", url="https://example.com/same"),
        SourceImportRow(title="B", url="https://example.com/same"),
    ]
    result = await service.preview_sources(rows)
    assert result.new_count == 1
    assert result.duplicate_count == 1


@pytest.mark.asyncio
async def test_preview_sources_authors_display(service):
    rows = [
        SourceImportRow(title="Single author", authors=["Smith, J"]),
        SourceImportRow(title="Multiple authors", authors=["Smith, J", "Doe, J", "Brown, K"]),
    ]
    result = await service.preview_sources(rows)
    assert result.rows[0].authors_display == "Smith, J"
    assert result.rows[1].authors_display == "Smith, J et al."


@pytest.mark.asyncio
async def test_preview_sources_row_limit(service):
    rows = [SourceImportRow(title=f"Source {i}", url=f"https://x.com/{i}") for i in range(MAX_IMPORT_ROWS + 1)]
    with pytest.raises(ValueError, match="row limit"):
        await service.preview_sources(rows)


# ---------------------------------------------------------------------------
# Source import execution tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_sources_creates_records(service, db_session):
    from sqlalchemy import select
    rows = [
        SourceImportRow(title="New drug A", url="https://example.com/a", kind="article", year=2021),
        SourceImportRow(title="New drug B", url="https://example.com/b"),
    ]
    result = await service.import_sources(rows)
    assert result.created == 2
    assert result.skipped_duplicates == 0
    assert result.failed == 0
    assert len(result.source_ids) == 2

    revisions = (await db_session.execute(
        select(SourceRevision).where(SourceRevision.title.in_(["New drug A", "New drug B"]))
    )).scalars().all()
    assert len(revisions) == 2


@pytest.mark.asyncio
async def test_import_sources_skips_duplicate_url(service, existing_source):
    rows = [SourceImportRow(title="Dup", url="https://doi.org/10.1234/aspirin")]
    result = await service.import_sources(rows)
    assert result.created == 0
    assert result.skipped_duplicates == 1


@pytest.mark.asyncio
async def test_import_sources_skips_invalid_rows(service):
    rows = [
        SourceImportRow(title="Valid source", url="https://example.com/valid"),
        SourceImportRow(title="", url="https://example.com/invalid"),
    ]
    result = await service.import_sources(rows)
    assert result.created == 1
    assert result.failed == 1


@pytest.mark.asyncio
async def test_import_sources_row_limit(service):
    rows = [SourceImportRow(title=f"S{i}", url=f"https://x.com/{i}") for i in range(MAX_IMPORT_ROWS + 1)]
    with pytest.raises(ValueError, match="row limit"):
        await service.import_sources(rows)
