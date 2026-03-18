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
