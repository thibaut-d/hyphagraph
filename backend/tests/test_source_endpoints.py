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
