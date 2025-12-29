"""
Tests for entity terms API endpoints.

Tests CRUD operations for entity terms (aliases/synonyms).
"""

import pytest
from uuid import uuid4
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from app.main import app
from app.database import get_db
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.ui_category import UiCategory
from app.models.user import User


@pytest.fixture
def override_get_db(db_session):
    """Override database dependency with test session."""
    async def _override_get_db():
        yield db_session
    return _override_get_db


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed",
        is_active=True,
        is_verified=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def override_auth(mock_user):
    """Override auth dependency with mock user."""
    from app.dependencies.auth import get_current_user
    return {get_current_user: lambda: mock_user}


@pytest.fixture
async def ui_category(db_session):
    """Create a test UI category."""
    db = db_session
    category = UiCategory(
        slug="test_category",
        labels={"en": "Test Category"},
        order=1
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@pytest.fixture
async def test_entity(db_session, ui_category):
    """Create a test entity for term tests."""
    db = db_session
    entity = Entity()
    db.add(entity)
    await db.flush()

    revision = EntityRevision(
        entity_id=entity.id,
        slug="paracetamol",
        summary={"en": "Pain relief medication"},
        ui_category_id=ui_category.id,
        is_current=True
    )
    db.add(revision)
    await db.commit()
    await db.refresh(entity)
    return entity


@pytest.fixture
async def test_entity_with_terms(db_session, test_entity):
    """Create an entity with existing terms."""
    db = db_session

    # Add three terms with different properties
    terms_data = [
        {"term": "Paracetamol", "language": "en", "display_order": 1},
        {"term": "Paracétamol", "language": "fr", "display_order": 2},
        {"term": "Acetaminophen", "language": "en", "display_order": 3},
    ]

    created_terms = []
    for data in terms_data:
        term = EntityTerm(
            entity_id=test_entity.id,
            **data
        )
        db.add(term)
        created_terms.append(term)

    await db.commit()
    for term in created_terms:
        await db.refresh(term)

    return test_entity, created_terms


# ===== List Terms Tests =====


@pytest.mark.asyncio
async def test_list_entity_terms_empty(override_get_db, test_entity):
    """Test listing terms for entity with no terms."""
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/entities/{test_entity.id}/terms")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_entity_terms_with_data(override_get_db, test_entity_with_terms):
    """Test listing terms returns all terms in correct order."""
    entity, created_terms = test_entity_with_terms

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/entities/{entity.id}/terms")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3

            # Verify order: display_order ascending
            assert data[0]["term"] == "Paracetamol"
            assert data[0]["display_order"] == 1
            assert data[1]["term"] == "Paracétamol"
            assert data[1]["display_order"] == 2
            assert data[2]["term"] == "Acetaminophen"
            assert data[2]["display_order"] == 3
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_entity_terms_nonexistent_entity(override_get_db):
    """Test listing terms for non-existent entity returns 404."""
    fake_id = uuid4()

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/entities/{fake_id}/terms")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


# ===== Create Term Tests =====


@pytest.mark.asyncio
async def test_create_entity_term(override_get_db, override_auth, test_entity):
    """Test creating a new term for an entity."""
    payload = {
        "term": "Tylenol",
        "language": "en",
        "display_order": 10
    }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.update(override_auth)
    app.dependency_overrides.update(override_auth)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/entities/{test_entity.id}/terms",
                json=payload
            )

            assert response.status_code == 201
            data = response.json()

            assert data["term"] == "Tylenol"
            assert data["language"] == "en"
            assert data["display_order"] == 10
            assert data["entity_id"] == str(test_entity.id)
            assert "id" in data
            assert "created_at" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_entity_term_minimal(override_get_db, override_auth, test_entity):
    """Test creating term with only required field (term)."""
    payload = {
        "term": "Acetaminophen"
    }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.update(override_auth)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            
                response = await client.post(
                    f"/api/entities/{test_entity.id}/terms",
                    json=payload
                )

                assert response.status_code == 201
                data = response.json()

                assert data["term"] == "Acetaminophen"
                assert data["language"] is None
                assert data["display_order"] is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_entity_term_duplicate(override_get_db, override_auth, test_entity_with_terms):
    """Test creating duplicate term fails with 409."""
    entity, _ = test_entity_with_terms

    # Try to create a term that already exists
    payload = {
        "term": "Paracetamol",
        "language": "en"
    }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.update(override_auth)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            
                response = await client.post(
                    f"/api/entities/{entity.id}/terms",
                    json=payload
                )

                assert response.status_code == 409
                assert "already exists" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_entity_term_requires_auth(override_get_db, test_entity):
    """Test creating term requires authentication."""
    payload = {"term": "Test"}

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/entities/{test_entity.id}/terms",
                json=payload
            )

            assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


# ===== Update Term Tests =====


@pytest.mark.asyncio
async def test_update_entity_term(override_get_db, override_auth, test_entity_with_terms):
    """Test updating an existing term."""
    entity, terms = test_entity_with_terms
    term_to_update = terms[0]

    payload = {
        "term": "Paracetamol Updated",
        "language": "en",
        "display_order": 99
    }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.update(override_auth)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            
                response = await client.put(
                    f"/api/entities/{entity.id}/terms/{term_to_update.id}",
                    json=payload
                )

                assert response.status_code == 200
                data = response.json()

                assert data["id"] == str(term_to_update.id)
                assert data["term"] == "Paracetamol Updated"
                assert data["display_order"] == 99
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_entity_term_to_duplicate(override_get_db, override_auth, test_entity_with_terms):
    """Test updating term to duplicate value fails."""
    entity, terms = test_entity_with_terms

    # Try to update first term to match second term
    payload = {
        "term": terms[1].term,  # "Paracétamol"
        "language": terms[1].language  # "fr"
    }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.update(override_auth)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            
                response = await client.put(
                    f"/api/entities/{entity.id}/terms/{terms[0].id}",
                    json=payload
                )

                assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()


# ===== Delete Term Tests =====


@pytest.mark.asyncio
async def test_delete_entity_term(override_get_db, override_auth, db_session, test_entity_with_terms):
    """Test deleting a term."""
    db = db_session
    entity, terms = test_entity_with_terms
    term_to_delete = terms[0]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.update(override_auth)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            
                response = await client.delete(
                    f"/api/entities/{entity.id}/terms/{term_to_delete.id}"
                )

                assert response.status_code == 204

                # Verify term was deleted
                stmt = select(EntityTerm).where(EntityTerm.id == term_to_delete.id)
                result = await db.execute(stmt)
                deleted_term = result.scalar_one_or_none()
                assert deleted_term is None
    finally:
        app.dependency_overrides.clear()


# ===== Bulk Update Tests =====


@pytest.mark.asyncio
async def test_bulk_update_entity_terms(override_get_db, override_auth, db_session, test_entity_with_terms):
    """Test bulk replacing all terms for an entity."""
    db = db_session
    entity, old_terms = test_entity_with_terms

    # New set of terms
    payload = {
        "terms": [
            {"term": "NewTerm1", "language": "en", "display_order": 1},
            {"term": "NewTerm2", "language": "fr", "display_order": 2},
        ]
    }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.update(override_auth)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            
                response = await client.put(
                    f"/api/entities/{entity.id}/terms-bulk",
                    json=payload
                )

                assert response.status_code == 200
                data = response.json()

                assert len(data) == 2
                assert data[0]["term"] == "NewTerm1"
                assert data[1]["term"] == "NewTerm2"

                # Verify old terms were deleted
                stmt = select(EntityTerm).where(EntityTerm.entity_id == entity.id)
                result = await db.execute(stmt)
                all_terms = result.scalars().all()

                assert len(all_terms) == 2
                assert all(term.id != old_terms[0].id for term in all_terms)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_bulk_update_entity_terms_duplicate_in_payload(override_get_db, override_auth, test_entity):
    """Test bulk update with duplicate terms in payload fails."""
    payload = {
        "terms": [
            {"term": "Duplicate", "language": "en"},
            {"term": "Duplicate", "language": "en"},  # Same term+lang
        ]
    }

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides.update(override_auth)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            
                response = await client.put(
                    f"/api/entities/{test_entity.id}/terms-bulk",
                    json=payload
                )

                assert response.status_code == 409
                assert "duplicate" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
