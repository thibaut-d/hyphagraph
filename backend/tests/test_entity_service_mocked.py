"""
Tests for EntityService using mocks (no database required).

Tests basic CRUD operations with mocked dependencies.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException

from app.services.entity_service import EntityService
from app.schemas.entity import EntityWrite, EntityRead
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_repo():
    """Mock entity repository."""
    return AsyncMock()


@pytest.fixture
def sample_entity():
    """Sample entity model."""
    entity = Entity()
    entity.id = uuid4()
    entity.created_at = datetime.now(timezone.utc)
    return entity


@pytest.fixture
def sample_revision():
    """Sample entity revision."""
    revision = EntityRevision()
    revision.id = uuid4()
    revision.entity_id = uuid4()
    revision.slug = "aspirin"
    revision.kind = "drug"
    revision.summary = {"en": "Pain reliever"}
    revision.is_current = True
    revision.created_at = datetime.now(timezone.utc)
    return revision


@pytest.mark.asyncio
class TestEntityServiceMocked:
    """Test EntityService with mocked dependencies."""

    async def test_create_entity_success(self, mock_db, sample_entity, sample_revision, monkeypatch):
        """Test successful entity creation."""
        # Arrange
        service = EntityService(mock_db)
        payload = EntityWrite(slug="aspirin", kind="drug", summary={"en": "Pain reliever"})

        # Mock the entity creation
        mock_db.flush.return_value = None
        sample_entity.id = uuid4()

        # Mock helper functions
        mock_create_revision = AsyncMock(return_value=sample_revision)
        monkeypatch.setattr("app.services.entity_service.create_new_revision", mock_create_revision)

        mock_to_read = MagicMock(return_value=EntityRead(
            id=sample_entity.id,
            slug="aspirin",
            kind="drug",
            summary={"en": "Pain reliever"},
            created_at=sample_entity.created_at,
        ))
        monkeypatch.setattr("app.services.entity_service.entity_to_read", mock_to_read)

        # Act
        result = await service.create(payload, user_id=uuid4())

        # Assert
        assert result.slug == "aspirin"
        assert result.kind == "drug"
        assert mock_db.commit.called
        assert mock_db.add.called

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
            await service.update(uuid4(), EntityWrite(slug="test", kind="drug"))

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

    async def test_list_all_entities(self, mock_db, mock_repo, sample_entity, sample_revision, monkeypatch):
        """Test listing all entities."""
        # Arrange
        service = EntityService(mock_db)
        service.repo = mock_repo

        # Mock repository returning entities
        mock_repo.list_all.return_value = [sample_entity]

        # Mock get_current_revision
        mock_get_revision = AsyncMock(return_value=sample_revision)
        monkeypatch.setattr("app.services.entity_service.get_current_revision", mock_get_revision)

        # Mock entity_to_read
        mock_to_read = MagicMock(return_value=EntityRead(
            id=sample_entity.id,
            slug=sample_revision.slug,
            kind=sample_revision.kind,
            summary=sample_revision.summary,
            created_at=sample_entity.created_at,
        ))
        monkeypatch.setattr("app.services.entity_service.entity_to_read", mock_to_read)

        # Act
        result = await service.list_all()

        # Assert
        assert len(result) == 1
        assert result[0].slug == "aspirin"

    async def test_create_entity_rollback_on_error(self, mock_db, monkeypatch):
        """Test that create rolls back on error."""
        # Arrange
        service = EntityService(mock_db)
        payload = EntityWrite(slug="test", kind="drug")

        # Mock flush to raise exception
        mock_db.flush.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception):
            await service.create(payload)

        # Verify rollback was called
        assert mock_db.rollback.called
