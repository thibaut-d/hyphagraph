"""
Integration tests for source API endpoints.
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from fastapi import status

from app.main import app
from app.database import get_db


@pytest.fixture
def override_get_db(db_session):
    """Override database dependency with test session."""
    async def _override_get_db():
        yield db_session
    return _override_get_db


@pytest.mark.asyncio
class TestSourceEndpoints:
    """Test source API endpoints."""

    async def test_list_sources(self, override_get_db):
        """Test listing sources."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/")
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]
        finally:
            app.dependency_overrides.clear()

    async def test_create_source_requires_auth(self, override_get_db):
        """Test creating source requires authentication."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/sources/",
                    json={"kind": "study", "title": "Test Study"}
                )
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    async def test_get_source(self, override_get_db):
        """Test getting specific source."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                source_id = uuid4()
                response = await client.get(f"/api/sources/{source_id}")
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        finally:
            app.dependency_overrides.clear()

    async def test_get_nonexistent_source(self, override_get_db):
        """Test getting non-existent source returns 404."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                fake_id = uuid4()
                response = await client.get(f"/api/sources/{fake_id}")
                assert response.status_code == status.HTTP_404_NOT_FOUND
        finally:
            app.dependency_overrides.clear()

    async def test_update_source_requires_auth(self, override_get_db):
        """Test updating source requires authentication."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                source_id = uuid4()
                response = await client.put(
                    f"/api/sources/{source_id}",
                    json={"kind": "review", "title": "Updated"}
                )
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    async def test_delete_source_requires_auth(self, override_get_db):
        """Test deleting source requires authentication."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                source_id = uuid4()
                response = await client.delete(f"/api/sources/{source_id}")
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    async def test_create_source_validation(self, override_get_db):
        """Test source creation validates required fields."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Missing required 'title'
                response = await client.post(
                    "/api/sources/",
                    json={"kind": "study"}
                )
                assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_401_UNAUTHORIZED]
        finally:
            app.dependency_overrides.clear()

    async def test_invalid_source_uuid(self, override_get_db):
        """Test invalid UUID in source endpoint."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/invalid-uuid")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_with_kind_filter(self, override_get_db):
        """Test filtering sources by kind."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?kind=article")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                # All returned sources should have kind='article' if any exist
                for source in data:
                    assert source.get('kind') == 'article'
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_with_multiple_kind_filters(self, override_get_db):
        """Test filtering sources by multiple kinds (OR logic)."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?kind=article&kind=book")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                # All returned sources should have kind in ['article', 'book']
                for source in data:
                    assert source.get('kind') in ['article', 'book']
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_with_year_min_filter(self, override_get_db):
        """Test filtering sources by minimum year."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?year_min=2020")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                # All returned sources should have year >= 2020 if year is set
                for source in data:
                    year = source.get('year')
                    if year is not None:
                        assert year >= 2020
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_with_year_max_filter(self, override_get_db):
        """Test filtering sources by maximum year."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?year_max=2023")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                # All returned sources should have year <= 2023 if year is set
                for source in data:
                    year = source.get('year')
                    if year is not None:
                        assert year <= 2023
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_with_year_range_filter(self, override_get_db):
        """Test filtering sources by year range."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?year_min=2020&year_max=2023")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                # All returned sources should have year in [2020, 2023]
                for source in data:
                    year = source.get('year')
                    if year is not None:
                        assert 2020 <= year <= 2023
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_with_trust_level_min_filter(self, override_get_db):
        """Test filtering sources by minimum trust level."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?trust_level_min=0.5")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                # All returned sources should have trust_level >= 0.5
                for source in data:
                    trust_level = source.get('trust_level')
                    if trust_level is not None:
                        assert trust_level >= 0.5
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_with_trust_level_max_filter(self, override_get_db):
        """Test filtering sources by maximum trust level."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?trust_level_max=0.8")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                # All returned sources should have trust_level <= 0.8
                for source in data:
                    trust_level = source.get('trust_level')
                    if trust_level is not None:
                        assert trust_level <= 0.8
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_with_trust_level_range_filter(self, override_get_db):
        """Test filtering sources by trust level range."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?trust_level_min=0.3&trust_level_max=0.7")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                # All returned sources should have trust_level in [0.3, 0.7]
                for source in data:
                    trust_level = source.get('trust_level')
                    if trust_level is not None:
                        assert 0.3 <= trust_level <= 0.7
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_with_search_filter(self, override_get_db):
        """Test searching sources by title, authors, or origin."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?search=study")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                # Results should contain 'study' in title, authors, or origin (case-insensitive)
                for source in data:
                    title = source.get('title', '').lower()
                    origin = source.get('origin', '').lower()
                    authors = str(source.get('authors', [])).lower()
                    assert 'study' in title or 'study' in origin or 'study' in authors
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_with_combined_filters(self, override_get_db):
        """Test combining multiple filters (AND logic between filter types)."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?kind=article&year_min=2020&trust_level_min=0.5")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
                # Results should match ALL filters
                for source in data:
                    assert source.get('kind') == 'article'
                    year = source.get('year')
                    if year is not None:
                        assert year >= 2020
                    trust_level = source.get('trust_level')
                    if trust_level is not None:
                        assert trust_level >= 0.5
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_year_validation_min_too_small(self, override_get_db):
        """Test that year_min validates minimum value."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?year_min=999")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_year_validation_max_too_large(self, override_get_db):
        """Test that year_max validates maximum value."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?year_max=10000")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_trust_level_validation_min_too_small(self, override_get_db):
        """Test that trust_level_min validates minimum value."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?trust_level_min=-0.1")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_trust_level_validation_max_too_large(self, override_get_db):
        """Test that trust_level_max validates maximum value."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?trust_level_max=1.1")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_search_too_long(self, override_get_db):
        """Test that search parameter validates max length."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Search term longer than 100 characters should be rejected
                long_search = "a" * 101
                response = await client.get(f"/api/sources/?search={long_search}")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()

    async def test_list_sources_empty_filters(self, override_get_db):
        """Test that empty filter values are ignored."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/sources/?kind=&search=")
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert isinstance(data, list)
        finally:
            app.dependency_overrides.clear()
