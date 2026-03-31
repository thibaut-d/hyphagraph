from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from app.api.revision_review import _get_service
from app.dependencies.auth import get_current_active_superuser, get_current_user
from app.main import app
from app.models.user import User
from app.services.revision_review_service import RevisionReviewService
from app.utils.errors import ForbiddenException


@pytest.fixture
def revision_review_service():
    service = AsyncMock(spec=RevisionReviewService)
    service.list_drafts.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 50,
        "has_more": False,
    }
    service.get_draft_counts.return_value = {
        "entity": 0,
        "relation": 0,
        "source": 0,
        "total": 0,
    }
    service.confirm.return_value = True
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


def _override_service(service: AsyncMock):
    def factory() -> AsyncMock:
        return service

    return factory


class TestRevisionReviewEndpointAuthorization:
    @pytest.mark.asyncio
    async def test_list_requires_superuser(self, revision_review_service, regular_user):
        async def override_current_user():
            return regular_user

        async def override_superuser():
            raise ForbiddenException(message="Superuser privileges required")

        app.dependency_overrides[get_current_user] = override_current_user
        app.dependency_overrides[get_current_active_superuser] = override_superuser
        app.dependency_overrides[_get_service] = _override_service(revision_review_service)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/review/revisions")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        revision_review_service.list_drafts.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_counts_requires_superuser(self, revision_review_service, regular_user):
        async def override_current_user():
            return regular_user

        async def override_superuser():
            raise ForbiddenException(message="Superuser privileges required")

        app.dependency_overrides[get_current_user] = override_current_user
        app.dependency_overrides[get_current_active_superuser] = override_superuser
        app.dependency_overrides[_get_service] = _override_service(revision_review_service)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/review/revisions/counts")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        revision_review_service.get_draft_counts.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_counts_response_shape(self, revision_review_service, superuser):
        """Counts endpoint must return exactly entity/relation/source/total as integers."""
        revision_review_service.get_draft_counts.return_value = {
            "entity": 3,
            "relation": 7,
            "source": 1,
            "total": 11,
        }

        async def override_superuser():
            return superuser

        app.dependency_overrides[get_current_active_superuser] = override_superuser
        app.dependency_overrides[_get_service] = _override_service(revision_review_service)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/review/revisions/counts")

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body == {"entity": 3, "relation": 7, "source": 1, "total": 11}
        # Ensure no unexpected keys leak through
        assert set(body.keys()) == {"entity", "relation", "source", "total"}

    @pytest.mark.asyncio
    async def test_confirm_passes_current_superuser_id(self, revision_review_service, superuser):
        revision_id = uuid4()

        async def override_superuser():
            return superuser

        app.dependency_overrides[get_current_active_superuser] = override_superuser
        app.dependency_overrides[_get_service] = _override_service(revision_review_service)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(f"/api/review/revisions/entity/{revision_id}/confirm")

        assert response.status_code == status.HTTP_200_OK
        revision_review_service.confirm.assert_awaited_once_with(
            "entity",
            revision_id,
            reviewed_by_user_id=superuser.id,
        )
