from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.api.service_dependencies import get_extraction_review_service
from app.dependencies.auth import get_current_active_superuser, get_current_user
from app.main import app
from app.models.user import User
from app.schemas.staged_extraction import StagedExtractionFilters
from app.utils.errors import ForbiddenException


@pytest.fixture
def review_service():
    service = AsyncMock()
    service.list_extractions.return_value = ([], 0)
    service.get_stats.return_value = {
        "total_pending": 0,
        "total_approved": 0,
        "total_rejected": 0,
        "total_auto_verified": 0,
        "pending_entities": 0,
        "pending_relations": 0,
        "pending_claims": 0,
        "avg_validation_score": 0.0,
        "high_confidence_count": 0,
        "flagged_count": 0,
    }
    service.get_extraction.return_value = {
        "id": uuid4(),
        "extraction_type": "entity",
        "status": "pending",
        "source_id": uuid4(),
        "extraction_data": {"slug": "aspirin"},
        "validation_score": 0.9,
        "validation_flags": [],
        "auto_commit_eligible": False,
        "llm_model": "gpt-4",
        "llm_provider": "openai",
        "created_at": datetime.now(timezone.utc),
        "reviewed_at": None,
        "review_notes": None,
        "materialized_entity_id": None,
        "materialized_relation_id": None,
        "confidence_adjustment": 1.0,
    }
    return service


@pytest.fixture
def regular_user():
    return User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def superuser():
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


class TestExtractionReviewEndpointAuthorization:
    @pytest.mark.asyncio
    async def test_pending_requires_superuser(self, review_service, regular_user):
        async def override_current_user():
            return regular_user

        async def override_superuser():
            raise ForbiddenException(
                message="Superuser privileges required",
                details="This action requires administrator privileges",
            )

        app.dependency_overrides[get_current_user] = override_current_user
        app.dependency_overrides[get_current_active_superuser] = override_superuser
        app.dependency_overrides[get_extraction_review_service] = lambda: review_service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/extraction-review/pending")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Superuser privileges required"
        review_service.list_extractions.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pending_allows_superuser(self, review_service, superuser):
        async def override_superuser():
            return superuser

        app.dependency_overrides[get_current_active_superuser] = override_superuser
        app.dependency_overrides[get_extraction_review_service] = lambda: review_service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/extraction-review/pending")

        assert response.status_code == status.HTTP_200_OK
        review_service.list_extractions.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stats_requires_superuser(self, review_service, regular_user):
        async def override_current_user():
            return regular_user

        async def override_superuser():
            raise ForbiddenException(
                message="Superuser privileges required",
                details="This action requires administrator privileges",
            )

        app.dependency_overrides[get_current_user] = override_current_user
        app.dependency_overrides[get_current_active_superuser] = override_superuser
        app.dependency_overrides[get_extraction_review_service] = lambda: review_service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/extraction-review/stats")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        review_service.get_stats.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_extraction_requires_superuser(self, review_service, regular_user):
        extraction_id = uuid4()

        async def override_current_user():
            return regular_user

        async def override_superuser():
            raise ForbiddenException(
                message="Superuser privileges required",
                details="This action requires administrator privileges",
            )

        app.dependency_overrides[get_current_user] = override_current_user
        app.dependency_overrides[get_current_active_superuser] = override_superuser
        app.dependency_overrides[get_extraction_review_service] = lambda: review_service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(f"/api/extraction-review/{extraction_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        review_service.get_extraction.assert_not_awaited()


class TestExtractionReviewPendingFilters:
    @pytest.mark.asyncio
    async def test_pending_passes_full_filter_contract(self, review_service, superuser):
        async def override_superuser():
            return superuser

        app.dependency_overrides[get_current_active_superuser] = override_superuser
        app.dependency_overrides[get_extraction_review_service] = lambda: review_service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/extraction-review/pending",
                params={
                    "extraction_type": "entity",
                    "min_validation_score": "0.2",
                    "max_validation_score": "0.8",
                    "has_flags": "true",
                    "auto_commit_eligible": "false",
                    "page": "3",
                    "page_size": "25",
                    "sort_by": "validation_score",
                    "sort_order": "asc",
                },
            )

        assert response.status_code == status.HTTP_200_OK
        review_service.list_extractions.assert_awaited_once()

        filters = review_service.list_extractions.await_args.args[0]
        assert isinstance(filters, StagedExtractionFilters)
        assert filters.status == "pending"
        assert filters.extraction_type == "entity"
        assert filters.min_validation_score == 0.2
        assert filters.max_validation_score == 0.8
        assert filters.has_flags is True
        assert filters.auto_commit_eligible is False
        assert filters.page == 3
        assert filters.page_size == 25
        assert filters.sort_by == "validation_score"
        assert filters.sort_order == "asc"

    @pytest.mark.asyncio
    async def test_pending_response_uses_filter_pagination(self, review_service, superuser):
        async def override_superuser():
            return superuser

        app.dependency_overrides[get_current_active_superuser] = override_superuser
        app.dependency_overrides[get_extraction_review_service] = lambda: review_service

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/extraction-review/pending",
                params={"page": "2", "page_size": "10"},
            )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["page"] == 2
        assert body["page_size"] == 10
        assert body["has_more"] is False
