from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.dependencies.auth import get_current_active_superuser
from app.main import app
from app.models.user import User


@pytest.fixture
def override_get_db(db_session):
    async def _override_get_db():
        yield db_session

    return _override_get_db


@pytest.fixture
def superuser():
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hashed",
        is_active=True,
        is_verified=True,
        is_superuser=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_graph_cleaning_analysis_requires_superuser(override_get_db):
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/admin/graph-cleaning/analysis")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_graph_cleaning_analysis_returns_read_only_shape(override_get_db, superuser):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = lambda: superuser
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/admin/graph-cleaning/analysis")
            assert response.status_code == status.HTTP_200_OK
            assert response.json() == {
                "duplicate_relations": [],
                "role_consistency": [],
            }
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_graph_cleaning_decision_endpoint_persists_decision(
    override_get_db,
    superuser,
    db_session,
):
    db_session.add(superuser)
    await db_session.commit()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = lambda: superuser
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/admin/graph-cleaning/decisions",
                json={
                    "candidate_type": "entity_merge",
                    "candidate_fingerprint": "candidate-1",
                    "status": "dismissed",
                    "notes": "Not a duplicate.",
                },
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == "dismissed"

            list_response = await client.get("/api/admin/graph-cleaning/decisions")
            assert list_response.status_code == status.HTTP_200_OK
            assert len(list_response.json()) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_graph_cleaning_critique_requires_configured_llm(
    override_get_db,
    superuser,
    monkeypatch,
):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_superuser] = lambda: superuser
    monkeypatch.setattr("app.api.graph_cleaning.is_llm_available", lambda: False)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/admin/graph-cleaning/critique",
                json={"candidates": [{"candidate_fingerprint": "candidate-1"}]},
            )
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    finally:
        app.dependency_overrides.clear()
