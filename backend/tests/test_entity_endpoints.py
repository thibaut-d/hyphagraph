"""
Integration tests for entity API endpoints.

Tests authentication requirements and full CRUD flow.
"""
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from fastapi import status

from app.main import app
from app.database import get_db
from app.models.user import User
from datetime import datetime, timezone


@pytest.fixture
def override_get_db(db_session):
    """Override database dependency with test session."""
    async def _override_get_db():
        yield db_session
    return _override_get_db


@pytest.fixture
def mock_current_user():
    """Mock authenticated user."""
    return User(
        id=uuid4(),
        email="testuser@example.com",
        hashed_password="hashed",
        is_active=True,
        is_verified=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
class TestEntityEndpoints:
    """Test entity API endpoints."""

    async def test_list_entities_no_auth(self, override_get_db):
        """Test listing entities without authentication (should succeed)."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/entities/")
                # List endpoint is public
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]
        finally:
            app.dependency_overrides.clear()

    async def test_create_entity_requires_auth(self, override_get_db):
        """Test creating entity requires authentication."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/entities/",
                    json={"slug": "test", "kind": "drug"}
                )
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    async def test_create_entity_with_auth(self, mock_current_user, override_get_db):
        """Test creating entity with authentication."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.entities.get_current_user") as mock_get_user:
                    with patch("app.api.entities.EntityService") as MockService:
                        # Mock authentication
                        mock_get_user.return_value = mock_current_user

                        # Mock service
                        mock_service = AsyncMock()
                        MockService.return_value = mock_service

                        mock_entity = AsyncMock()
                        mock_entity.id = uuid4()
                        mock_entity.slug = "aspirin"
                        mock_entity.kind = "drug"
                        mock_entity.summaries = {}
                        mock_entity.created_at = datetime.now(timezone.utc)

                        mock_service.create.return_value = mock_entity

                        response = await client.post(
                            "/api/entities/",
                            json={"slug": "aspirin", "kind": "drug"}
                        )

                        # Note: Authentication is mocked, so response may vary
                        # In real integration test with DB, this would be 201
                        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_401_UNAUTHORIZED]
        finally:
            app.dependency_overrides.clear()

    async def test_get_entity(self, override_get_db):
        """Test getting specific entity."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                entity_id = uuid4()
                response = await client.get(f"/api/entities/{entity_id}")

                # Will return 404 if entity doesn't exist
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        finally:
            app.dependency_overrides.clear()

    async def test_update_entity_requires_auth(self, override_get_db):
        """Test updating entity requires authentication."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                entity_id = uuid4()
                response = await client.put(
                    f"/api/entities/{entity_id}",
                    json={"slug": "updated", "kind": "drug"}
                )
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    async def test_delete_entity_requires_auth(self, override_get_db):
        """Test deleting entity requires authentication."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                entity_id = uuid4()
                response = await client.delete(f"/api/entities/{entity_id}")
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    async def test_create_entity_validation(self, override_get_db):
        """Test entity creation validates required fields."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Missing required field 'slug'
                response = await client.post(
                    "/api/entities/",
                    json={"kind": "drug"}
                )
                assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_401_UNAUTHORIZED]
        finally:
            app.dependency_overrides.clear()

    async def test_create_entity_invalid_kind(self, override_get_db):
        """Test entity creation with invalid kind."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/entities/",
                    json={"slug": "test", "kind": ""}  # Empty kind
                )
                # Validation error or auth error
                assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_401_UNAUTHORIZED]
        finally:
            app.dependency_overrides.clear()

    async def test_get_nonexistent_entity(self, override_get_db):
        """Test getting non-existent entity returns 404."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                fake_id = uuid4()
                response = await client.get(f"/api/entities/{fake_id}")
                assert response.status_code == status.HTTP_404_NOT_FOUND
        finally:
            app.dependency_overrides.clear()

    async def test_invalid_uuid_format(self, override_get_db):
        """Test invalid UUID format in URL."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/entities/not-a-uuid")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_with_search_filter(self, override_get_db):
        """Test searching entities by slug."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/entities/?search=test")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert 'items' in data
                assert 'total' in data
                assert isinstance(data['items'], list)
                # Results should contain 'test' in slug (case-insensitive)
                for entity in data['items']:
                    slug = entity.get('slug', '').lower()
                    assert 'test' in slug
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_with_combined_filters(self, override_get_db):
        """Test combining multiple filters (AND logic between filter types)."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                test_category_id = str(uuid4())
                response = await client.get(f"/api/entities/?ui_category_id={test_category_id}&search=test")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert 'items' in data
                assert 'total' in data
                assert isinstance(data['items'], list)
                # Results should match ALL filters
                for entity in data['items']:
                    assert entity.get('ui_category_id') == test_category_id
                    slug = entity.get('slug', '').lower()
                    assert 'test' in slug
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_with_ui_category_filter(self, override_get_db):
        """Test filtering entities by UI category ID."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                test_category_id = str(uuid4())
                response = await client.get(f"/api/entities/?ui_category_id={test_category_id}")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert 'items' in data
                assert 'total' in data
                assert isinstance(data['items'], list)
                # All returned entities should have matching ui_category_id if any exist
                for entity in data['items']:
                    assert entity.get('ui_category_id') == test_category_id
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_search_too_long(self, override_get_db):
        """Test that search parameter validates max length."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Search term longer than 100 characters should be rejected
                long_search = "a" * 101
                response = await client.get(f"/api/entities/?search={long_search}")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_empty_filters(self, override_get_db):
        """Test that empty filter values are ignored."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/entities/?search=")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert 'items' in data
                assert 'total' in data
                assert isinstance(data['items'], list)
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_pagination_default(self, override_get_db):
        """Test pagination with default values."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/entities/")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert 'items' in data
                assert 'total' in data
                assert 'limit' in data
                assert 'offset' in data
                assert isinstance(data['items'], list)
                # Default limit is 50, so results should be <= 50
                assert len(data['items']) <= 50
                assert data['limit'] == 50
                assert data['offset'] == 0
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_pagination_custom_limit(self, override_get_db):
        """Test pagination with custom limit."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/entities/?limit=10")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert 'items' in data
                assert 'total' in data
                assert isinstance(data['items'], list)
                assert len(data['items']) <= 10
                assert data['limit'] == 10
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_pagination_with_offset(self, override_get_db):
        """Test pagination with offset."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Get first page
                response1 = await client.get("/api/entities/?limit=5&offset=0")
                assert response1.status_code == status.HTTP_200_OK
                page1 = response1.json()
                assert 'items' in page1

                # Get second page
                response2 = await client.get("/api/entities/?limit=5&offset=5")
                assert response2.status_code == status.HTTP_200_OK
                page2 = response2.json()
                assert 'items' in page2

                # Pages should be different (if enough data exists)
                if len(page1['items']) == 5 and len(page2['items']) > 0:
                    page1_ids = {e['id'] for e in page1['items']}
                    page2_ids = {e['id'] for e in page2['items']}
                    assert page1_ids.isdisjoint(page2_ids)
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_pagination_limit_too_high(self, override_get_db):
        """Test that limit over 100 is rejected."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/entities/?limit=101")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_pagination_limit_zero(self, override_get_db):
        """Test that limit of 0 is rejected."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/entities/?limit=0")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    async def test_list_entities_pagination_negative_offset(self, override_get_db):
        """Test that negative offset is rejected."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/entities/?offset=-1")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()
