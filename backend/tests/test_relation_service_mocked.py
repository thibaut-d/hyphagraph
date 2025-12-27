"""
Tests for RelationService using mocks (no database required).

Tests critical business logic: source_id immutability.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from fastapi import HTTPException

from app.services.relation_service import RelationService
from app.schemas.relation import RelationWrite, RoleRevisionWrite as RoleWrite
from app.models.relation import Relation


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_repo():
    """Mock relation repository."""
    return AsyncMock()


@pytest.fixture
def sample_relation():
    """Sample relation model."""
    relation = Relation()
    relation.id = uuid4()
    relation.source_id = uuid4()
    return relation


@pytest.mark.asyncio
class TestRelationServiceMocked:
    """Test RelationService with mocked dependencies."""

    async def test_get_relation_not_found(self, mock_db, mock_repo):
        """Test getting non-existent relation raises 404."""
        # Arrange
        service = RelationService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.get(uuid4())

        assert exc_info.value.status_code == 404

    async def test_delete_relation_not_found(self, mock_db, mock_repo):
        """Test deleting non-existent relation raises 404."""
        # Arrange
        service = RelationService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.delete(uuid4())

        assert exc_info.value.status_code == 404

    async def test_update_relation_source_id_immutable(self, mock_db, mock_repo, sample_relation):
        """Test that changing source_id raises error (critical business rule)."""
        # Arrange
        service = RelationService(mock_db)
        service.repo = mock_repo

        # Mock getting existing relation
        original_source_id = sample_relation.source_id
        mock_repo.get_by_id.return_value = sample_relation

        # Try to update with different source_id
        different_source_id = uuid4()
        payload = RelationWrite(
            source_id=str(different_source_id),
            kind="effect",
            direction="positive",
            roles=[]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update(sample_relation.id, payload)

        assert exc_info.value.status_code == 400
        assert "cannot change source_id" in exc_info.value.detail.lower()

    async def test_update_relation_not_found(self, mock_db, mock_repo):
        """Test updating non-existent relation raises 404."""
        # Arrange
        service = RelationService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        payload = RelationWrite(
            source_id=str(uuid4()),
            kind="effect",
            direction="positive",
            roles=[]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update(uuid4(), payload)

        assert exc_info.value.status_code == 404

    async def test_list_by_source(self, mock_db, mock_repo, monkeypatch):
        """Test listing relations by source."""
        # Arrange
        service = RelationService(mock_db)
        service.repo = mock_repo

        source_id = uuid4()
        mock_relations = [MagicMock(), MagicMock()]
        mock_repo.list_by_source.return_value = mock_relations

        # Mock relation_to_read
        mock_to_read = MagicMock()
        monkeypatch.setattr("app.services.relation_service.relation_to_read", mock_to_read)

        # Act
        result = await service.list_by_source(str(source_id))

        # Assert
        mock_repo.list_by_source.assert_called_once_with(str(source_id))
        assert mock_to_read.call_count == 2
