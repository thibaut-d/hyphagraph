"""
Tests for SourceService using mocks (no database required).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
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
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def mock_repo():
    """Mock source repository."""
    return AsyncMock()


@pytest.mark.asyncio
class TestSourceServiceMocked:
    """Test SourceService with mocked dependencies."""

    async def test_get_source_not_found(self, mock_db, mock_repo):
        """Test getting non-existent source raises 404."""
        # Arrange
        service = SourceService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.get(uuid4())

        assert exc_info.value.status_code == 404

    async def test_update_source_not_found(self, mock_db, mock_repo):
        """Test updating non-existent source raises 404."""
        # Arrange
        service = SourceService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update(uuid4(), SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        assert exc_info.value.status_code == 404

    async def test_delete_source_not_found(self, mock_db, mock_repo):
        """Test deleting non-existent source raises 404."""
        # Arrange
        service = SourceService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.delete(uuid4())

        assert exc_info.value.status_code == 404

    async def test_create_source_rollback_on_error(self, mock_db):
        """Test that create rolls back on error."""
        # Arrange
        service = SourceService(mock_db)
        payload = SourceWrite(kind="study", title="Test", url="https://example.com/test")

        # Mock to raise exception
        mock_db.flush.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):
            await service.create(payload)

        assert mock_db.rollback.called

    async def test_get_filter_options_uses_injected_derived_properties_service(
        self, mock_db
    ):
        """Test source filter options use the injected derived properties collaborator."""
        derived_service = AsyncMock()
        derived_service.get_all_domains.return_value = ["neurology", "rheumatology"]

        kind_result = MagicMock()
        kind_result.all = MagicMock(return_value=[("study",), ("review",)])
        year_result = MagicMock()
        year_result.one = MagicMock(return_value=(1999, 2024))
        mock_db.execute = AsyncMock(side_effect=[kind_result, year_result])

        service = SourceService(mock_db, derived_properties_service=derived_service)

        result = await service.get_filter_options()

        assert result.kinds == ["review", "study"]
        assert result.year_range == (1999, 2024)
        assert result.domains == ["neurology", "rheumatology"]
        derived_service.get_all_domains.assert_awaited_once()
