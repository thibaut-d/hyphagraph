"""
Integration tests for relation API endpoints.
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
class TestRelationEndpoints:
    """Test relation API endpoints."""

    async def test_create_relation_requires_auth(self, override_get_db):
        """Test creating relation requires authentication."""
        app.dependency_overrides[get_db] = override_get_db
        try:
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
        finally:
            app.dependency_overrides.clear()

    async def test_get_relation(self, override_get_db):
        """Test getting specific relation."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                relation_id = uuid4()
                response = await client.get(f"/api/relations/{relation_id}")
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        finally:
            app.dependency_overrides.clear()

    async def test_get_nonexistent_relation(self, override_get_db):
        """Test getting non-existent relation returns 404."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                fake_id = uuid4()
                response = await client.get(f"/api/relations/{fake_id}")
                assert response.status_code == status.HTTP_404_NOT_FOUND
        finally:
            app.dependency_overrides.clear()

    async def test_list_relations_by_source(self, override_get_db):
        """Test listing relations by source."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                source_id = uuid4()
                response = await client.get(f"/api/relations/source/{source_id}")
                # Returns 404 if source doesn't exist, 200 if it exists (even with no relations)
                assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        finally:
            app.dependency_overrides.clear()

    async def test_update_relation_requires_auth(self, override_get_db):
        """Test updating relation requires authentication."""
        app.dependency_overrides[get_db] = override_get_db
        try:
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
        finally:
            app.dependency_overrides.clear()

    async def test_delete_relation_requires_auth(self, override_get_db):
        """Test deleting relation requires authentication."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                relation_id = uuid4()
                response = await client.delete(f"/api/relations/{relation_id}")
                assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            app.dependency_overrides.clear()

    async def test_create_relation_validation(self, override_get_db):
        """Test relation creation validates required fields."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Missing required fields
                response = await client.post(
                    "/api/relations/",
                    json={"kind": "effect"}
                )
                assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_401_UNAUTHORIZED]
        finally:
            app.dependency_overrides.clear()

    async def test_invalid_relation_uuid(self, override_get_db):
        """Test invalid UUID in relation endpoint."""
        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/relations/not-a-uuid")
                assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        finally:
            app.dependency_overrides.clear()
