"""
Integration tests for source API endpoints.
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from fastapi import status

from app.main import app


@pytest.mark.asyncio
class TestSourceEndpoints:
    """Test source API endpoints."""

    async def test_list_sources(self):
        """Test listing sources."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/sources/")
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]

    async def test_create_source_requires_auth(self):
        """Test creating source requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/sources/",
                json={"kind": "study", "title": "Test Study"}
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_source(self):
        """Test getting specific source."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            source_id = uuid4()
            response = await client.get(f"/api/sources/{source_id}")
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    async def test_get_nonexistent_source(self):
        """Test getting non-existent source returns 404."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            fake_id = uuid4()
            response = await client.get(f"/api/sources/{fake_id}")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_source_requires_auth(self):
        """Test updating source requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            source_id = uuid4()
            response = await client.put(
                f"/api/sources/{source_id}",
                json={"kind": "review", "title": "Updated"}
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_delete_source_requires_auth(self):
        """Test deleting source requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            source_id = uuid4()
            response = await client.delete(f"/api/sources/{source_id}")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_source_validation(self):
        """Test source creation validates required fields."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Missing required 'title'
            response = await client.post(
                "/api/sources/",
                json={"kind": "study"}
            )
            assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_401_UNAUTHORIZED]

    async def test_invalid_source_uuid(self):
        """Test invalid UUID in source endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/sources/invalid-uuid")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
