"""
Simple tests for RelationService using mocks.

Tests critical business rule: source_id immutability.
"""
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from fastapi import HTTPException

from app.services.relation_service import RelationService
from app.schemas.relation import RelationWrite, RoleRevisionWrite
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
class TestRelationServiceSimple:
    """Test RelationService critical business rules."""

    async def test_get_relation_not_found(self, mock_db, mock_repo):
        """Test getting non-existent relation raises 404."""
        service = RelationService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.get(uuid4())

        assert exc_info.value.status_code == 404

    async def test_delete_relation_not_found(self, mock_db, mock_repo):
        """Test deleting non-existent relation raises 404."""
        service = RelationService(mock_db)
        service.repo = mock_repo
        mock_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await service.delete(uuid4())

        assert exc_info.value.status_code == 404

    async def test_update_relation_source_id_immutable(self, mock_db, mock_repo, sample_relation):
        """
        Test that changing source_id raises error.
        
        This is a CRITICAL business rule: Relations are immutable to their source.
        Once created, a relation cannot be moved to a different source.
        """
        service = RelationService(mock_db)
        service.repo = mock_repo

        # Mock getting existing relation
        original_source_id = sample_relation.source_id
        mock_repo.get_by_id.return_value = sample_relation

        # Try to update with different source_id (should fail)
        different_source_id = uuid4()
        payload = RelationWrite(
            source_id=different_source_id,
            kind="effect",
            direction="positive",
            confidence=0.9,
            roles=[RoleRevisionWrite(role_type="drug", entity_id=uuid4())]
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update(sample_relation.id, payload)

        # Verify it's a 400 error about immutability
        assert exc_info.value.status_code == 400
        assert "cannot change source_id" in exc_info.value.detail.lower()
