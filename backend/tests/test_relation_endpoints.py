"""
Integration tests for relation API endpoints.
"""
import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from fastapi import status

from app.main import app


@pytest.mark.asyncio
class TestRelationEndpoints:
    """Test relation API endpoints."""

    async def test_create_relation_requires_auth(self):
        """Test creating relation requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/relations/",
                json={
                    "source_id": str(uuid4()),
                    "kind": "effect",
                    "direction": "positive",
                    "roles": []
                }
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_relation(self):
        """Test getting specific relation."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            relation_id = uuid4()
            response = await client.get(f"/api/relations/{relation_id}")
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    async def test_get_nonexistent_relation(self):
        """Test getting non-existent relation returns 404."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            fake_id = uuid4()
            response = await client.get(f"/api/relations/{fake_id}")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_list_relations_by_source(self):
        """Test listing relations by source."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            source_id = uuid4()
            response = await client.get(f"/api/relations/source/{source_id}")
            # Returns empty list if source has no relations
            assert response.status_code == status.HTTP_200_OK

    async def test_update_relation_requires_auth(self):
        """Test updating relation requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            relation_id = uuid4()
            response = await client.put(
                f"/api/relations/{relation_id}",
                json={
                    "source_id": str(uuid4()),
                    "kind": "mechanism",
                    "direction": "positive",
                    "roles": []
                }
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_delete_relation_requires_auth(self):
        """Test deleting relation requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            relation_id = uuid4()
            response = await client.delete(f"/api/relations/{relation_id}")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_relation_validation(self):
        """Test relation creation validates required fields."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Missing required fields
            response = await client.post(
                "/api/relations/",
                json={"kind": "effect"}
            )
            assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_401_UNAUTHORIZED]

    async def test_invalid_relation_uuid(self):
        """Test invalid UUID in relation endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/relations/not-a-uuid")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
