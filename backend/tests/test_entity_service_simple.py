"""
Simple tests for EntityService using mocks (no database required).

Tests basic error handling.
"""
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from fastapi import HTTPException

from app.services.entity_service import EntityService
from app.schemas.entity import EntityWrite


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_repo():
    """Mock entity repository."""
    return AsyncMock()


@pytest.mark.asyncio
class TestEntityServiceSimple:
    """Test EntityService error handling with mocks."""

    async def test_get_entity_not_found(self, mock_db, mock_repo):
        """Test getting non-existent entity raises 404."""
        # Arrange
        service = EntityService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.get(uuid4())

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    async def test_update_entity_not_found(self, mock_db, mock_repo):
        """Test updating non-existent entity raises 404."""
        # Arrange
        service = EntityService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update(uuid4(), EntityWrite(slug="test"))

        assert exc_info.value.status_code == 404

    async def test_delete_entity_not_found(self, mock_db, mock_repo):
        """Test deleting non-existent entity raises 404."""
        # Arrange
        service = EntityService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.delete(uuid4())

        assert exc_info.value.status_code == 404

    async def test_create_entity_rollback_on_error(self, mock_db):
        """Test that create rolls back on error."""
        # Arrange
        service = EntityService(mock_db)
        payload = EntityWrite(slug="test")

        # Mock flush to raise exception
        mock_db.flush.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):
            await service.create(payload)

        # Verify rollback was called
        assert mock_db.rollback.called
