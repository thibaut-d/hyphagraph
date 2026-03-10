"""
Tests for EntityService.

Tests entity CRUD operations with revision tracking.
Uses scientifically accurate fibromyalgia/chronic pain test data.
"""
import pytest
from uuid import uuid4
from fastapi import HTTPException

from app.services.entity_service import EntityService
from app.schemas.entity import EntityWrite
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from fixtures.scientific_data import ScientificEntities


@pytest.mark.asyncio
class TestEntityService:
    """Test EntityService CRUD operations."""

    async def test_create_entity(self, db_session):
        """Test creating a new entity with first revision."""
        # Arrange
        service = EntityService(db_session)
        entity_data = ScientificEntities.PREGABALIN
        payload = EntityWrite(
            slug=entity_data["slug"],
            kind="drug",  # Legacy field, ignored
            summary=entity_data["summary"],
        )

        # Act
        result = await service.create(payload)

        # Assert
        assert result.slug == "pregabalin"
        assert "FDA-approved anticonvulsant" in result.summary["en"]
        assert result.id is not None
        assert result.created_at is not None

    async def test_create_entity_minimal(self, db_session):
        """Test creating entity with only required fields."""
        # Arrange
        service = EntityService(db_session)
        entity_data = ScientificEntities.DULOXETINE
        payload = EntityWrite(slug=entity_data["slug"], kind="drug")  # kind is legacy, ignored

        # Act
        result = await service.create(payload)

        # Assert
        assert result.slug == "duloxetine"
        assert result.summary is None or result.summary == {}

    async def test_get_entity(self, db_session):
        """Test retrieving an existing entity."""
        # Arrange
        service = EntityService(db_session)
        entity_data = ScientificEntities.MILNACIPRAN
        created = await service.create(
            EntityWrite(slug=entity_data["slug"], kind="drug"),  # kind is legacy, ignored

        )

        # Act
        result = await service.get(created.id)

        # Assert
        assert result.id == created.id
        assert result.slug == "milnacipran"

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
        await service.create(EntityWrite(slug=ScientificEntities.AMITRIPTYLINE["slug"], kind="drug"))
        await service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
        await service.create(EntityWrite(slug=ScientificEntities.FIBROMYALGIA["slug"], kind="disease"))

        # Act
        items, total = await service.list_all()

        # Assert
        assert len(items) == 3
        assert total == 3
        slugs = {e.slug for e in items}
        assert slugs == {"amitriptyline", "gabapentin", "fibromyalgia"}

    async def test_list_all_empty(self, db_session):
        """Test listing entities when none exist."""
        # Arrange
        service = EntityService(db_session)

        # Act
        items, total = await service.list_all()

        # Assert
        assert items == []
        assert total == 0

    async def test_update_entity(self, db_session):
        """Test updating an entity creates new revision."""
        # Arrange
        service = EntityService(db_session)
        created = await service.create(
            EntityWrite(slug="cyclobenzaprine", kind="drug", summary={"en": "Muscle relaxant"}),

        )

        # Act
        updated = await service.update(
            created.id,
            EntityWrite(slug="cyclobenzaprine", kind="drug", summary={"en": "Muscle relaxant used off-label for fibromyalgia"}),

        )

        # Assert
        assert updated.id == created.id  # Same entity ID
        assert updated.slug == "cyclobenzaprine"  # New data
        assert "off-label for fibromyalgia" in updated.summary["en"]

        # Verify we can still retrieve the updated version
        retrieved = await service.get(created.id)
        assert "off-label for fibromyalgia" in retrieved.summary["en"]

    async def test_update_entity_not_found(self, db_session):
        """Test updating non-existent entity raises 404."""
        # Arrange
        service = EntityService(db_session)
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.update(
                fake_id,
                EntityWrite(slug=ScientificEntities.TRAMADOL["slug"], kind="drug")
            )

        assert exc_info.value.status_code == 404

    async def test_delete_entity(self, db_session):
        """Test deleting an entity."""
        # Arrange
        service = EntityService(db_session)
        entity_data = ScientificEntities.ACETAMINOPHEN
        created = await service.create(EntityWrite(slug=entity_data["slug"], kind="drug"))

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
        entity_data = ScientificEntities.LOW_DOSE_NALTREXONE
        created = await service.create(EntityWrite(slug=entity_data["slug"], kind="drug", summary={"en": "Version 1"}))

        # Act - Create multiple revisions
        v2 = await service.update(created.id, EntityWrite(slug=entity_data["slug"], kind="drug", summary={"en": "Version 2"}))
        v3 = await service.update(created.id, EntityWrite(slug=entity_data["slug"], kind="drug", summary={"en": "Version 3"}))

        # Assert - Latest revision is returned
        current = await service.get(created.id)
        assert current.summary["en"] == "Version 3"
        assert current.id == created.id == v2.id == v3.id

    async def test_create_duplicate_slug_rejected(self, db_session):
        """Test that creating two entities with the same slug is rejected."""
        # Arrange
        service = EntityService(db_session)
        entity_data = ScientificEntities.TRAMADOL
        await service.create(EntityWrite(slug=entity_data["slug"], kind="drug"))

        # Act & Assert - Attempting to create another entity with the same slug should fail
        with pytest.raises(HTTPException) as exc_info:
            await service.create(EntityWrite(slug=entity_data["slug"], kind="drug"))

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail.lower()
