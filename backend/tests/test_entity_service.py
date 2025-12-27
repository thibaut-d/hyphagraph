"""
Tests for EntityService.

Tests entity CRUD operations with revision tracking.
"""
import pytest
from uuid import uuid4
from fastapi import HTTPException

from app.services.entity_service import EntityService
from app.schemas.entity import EntityWrite
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision


@pytest.mark.asyncio
class TestEntityService:
    """Test EntityService CRUD operations."""

    async def test_create_entity(self, db_session):
        """Test creating a new entity with first revision."""
        # Arrange
        service = EntityService(db_session)
        payload = EntityWrite(
            slug="aspirin",
            kind="drug",  # Legacy field, ignored
            summary={"en": "Pain reliever"},
        )

        # Act
        result = await service.create(payload)

        # Assert
        assert result.slug == "aspirin"
        assert result.summary["en"] == "Pain reliever"
        assert result.id is not None
        assert result.created_at is not None

    async def test_create_entity_minimal(self, db_session):
        """Test creating entity with only required fields."""
        # Arrange
        service = EntityService(db_session)
        payload = EntityWrite(slug="ibuprofen", kind="drug")  # kind is legacy, ignored

        # Act
        result = await service.create(payload)

        # Assert
        assert result.slug == "ibuprofen"
        assert result.summary is None or result.summary == {}

    async def test_get_entity(self, db_session):
        """Test retrieving an existing entity."""
        # Arrange
        service = EntityService(db_session)
        created = await service.create(
            EntityWrite(slug="paracetamol", kind="drug"),  # kind is legacy, ignored

        )

        # Act
        result = await service.get(created.id)

        # Assert
        assert result.id == created.id
        assert result.slug == "paracetamol"

    async def test_get_entity_not_found(self, db_session):
        """Test getting non-existent entity raises 404."""
        # Arrange
        service = EntityService(db_session)
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.get(fake_id)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    async def test_list_all_entities(self, db_session):
        """Test listing all entities."""
        # Arrange
        service = EntityService(db_session)
        await service.create(EntityWrite(slug="drug1", kind="drug"))
        await service.create(EntityWrite(slug="drug2", kind="drug"))
        await service.create(EntityWrite(slug="disease1", kind="disease"))

        # Act
        result = await service.list_all()

        # Assert
        assert len(result) == 3
        slugs = {e.slug for e in result}
        assert slugs == {"drug1", "drug2", "disease1"}

    async def test_list_all_empty(self, db_session):
        """Test listing entities when none exist."""
        # Arrange
        service = EntityService(db_session)

        # Act
        result = await service.list_all()

        # Assert
        assert result == []

    async def test_update_entity(self, db_session):
        """Test updating an entity creates new revision."""
        # Arrange
        service = EntityService(db_session)
        created = await service.create(
            EntityWrite(slug="original", kind="drug", summary={"en": "Original"}),
            
        )

        # Act
        updated = await service.update(
            created.id,
            EntityWrite(slug="updated", kind="drug", summary={"en": "Updated"}),
            
        )

        # Assert
        assert updated.id == created.id  # Same entity ID
        assert updated.slug == "updated"  # New data
        assert updated.summary["en"] == "Updated"

        # Verify we can still retrieve the updated version
        retrieved = await service.get(created.id)
        assert retrieved.slug == "updated"

    async def test_update_entity_not_found(self, db_session):
        """Test updating non-existent entity raises 404."""
        # Arrange
        service = EntityService(db_session)
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update(
                fake_id,
                EntityWrite(slug="test", kind="drug")
            )

        assert exc_info.value.status_code == 404

    async def test_delete_entity(self, db_session):
        """Test deleting an entity."""
        # Arrange
        service = EntityService(db_session)
        created = await service.create(EntityWrite(slug="todelete", kind="drug"))

        # Act
        await service.delete(created.id)

        # Assert - entity should not be retrievable
        with pytest.raises(HTTPException) as exc_info:
            await service.get(created.id)
        assert exc_info.value.status_code == 404

    async def test_delete_entity_not_found(self, db_session):
        """Test deleting non-existent entity raises 404."""
        # Arrange
        service = EntityService(db_session)
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.delete(fake_id)

        assert exc_info.value.status_code == 404

    async def test_multiple_revisions(self, db_session):
        """Test that multiple updates create proper revision history."""
        # Arrange
        service = EntityService(db_session)
        created = await service.create(EntityWrite(slug="v1", kind="drug"))

        # Act - Create multiple revisions
        v2 = await service.update(created.id, EntityWrite(slug="v2", kind="drug"))
        v3 = await service.update(created.id, EntityWrite(slug="v3", kind="drug"))

        # Assert - Latest revision is returned
        current = await service.get(created.id)
        assert current.slug == "v3"
        assert current.id == created.id == v2.id == v3.id
