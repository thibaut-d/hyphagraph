"""
Simple tests for SourceService using mocks.
"""
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from fastapi import HTTPException

from app.services.source_service import SourceService
from app.schemas.source import SourceWrite


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_repo():
    """Mock source repository."""
    return AsyncMock()


@pytest.mark.asyncio
class TestSourceServiceSimple:
    """Test SourceService error handling."""

    async def test_get_source_not_found(self, mock_db, mock_repo):
        """Test getting non-existent source raises 404."""
        service = SourceService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.get(uuid4())

        assert exc_info.value.status_code == 404

    async def test_update_source_not_found(self, mock_db, mock_repo):
        """Test updating non-existent source raises 404."""
        service = SourceService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.update(uuid4(), SourceWrite(kind="study", title="Test", url="https://example.com"))

        assert exc_info.value.status_code == 404

    async def test_delete_source_not_found(self, mock_db, mock_repo):
        """Test deleting non-existent source raises 404."""
        service = SourceService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.delete(uuid4())

        assert exc_info.value.status_code == 404
