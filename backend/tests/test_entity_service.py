"""
Tests for EntityService.

Tests entity CRUD operations with revision tracking.
Uses scientifically accurate fibromyalgia/chronic pain test data.
"""
import pytest
from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException

from app.services.entity_service import EntityService
from app.schemas.entity import EntityWrite
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
        payload = EntityWrite(slug=entity_data["slug"])

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
            EntityWrite(slug=entity_data["slug"]),

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
        await service.create(EntityWrite(slug=ScientificEntities.AMITRIPTYLINE["slug"]))
        await service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"]))
        await service.create(EntityWrite(slug=ScientificEntities.FIBROMYALGIA["slug"]))

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
            EntityWrite(slug="cyclobenzaprine", summary={"en": "Muscle relaxant"}),

        )

        # Act
        updated = await service.update(
            created.id,
            EntityWrite(slug="cyclobenzaprine", summary={"en": "Muscle relaxant used off-label for fibromyalgia"}),

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
                EntityWrite(slug=ScientificEntities.TRAMADOL["slug"])
            )

        assert exc_info.value.status_code == 404

    async def test_delete_entity(self, db_session):
        """Test deleting an entity."""
        # Arrange
        service = EntityService(db_session)
        entity_data = ScientificEntities.ACETAMINOPHEN
        created = await service.create(EntityWrite(slug=entity_data["slug"]))

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
        created = await service.create(EntityWrite(slug=entity_data["slug"], summary={"en": "Version 1"}))

        # Act - Create multiple revisions
        v2 = await service.update(created.id, EntityWrite(slug=entity_data["slug"], summary={"en": "Version 2"}))
        v3 = await service.update(created.id, EntityWrite(slug=entity_data["slug"], summary={"en": "Version 3"}))

        # Assert - Latest revision is returned
        current = await service.get(created.id)
        assert current.summary["en"] == "Version 3"
        assert current.id == created.id == v2.id == v3.id

    async def test_create_entity_with_user_id_sets_created_by(self, db_session):
        """create() with a user_id should record it on the EntityRevision."""
        from datetime import timezone
        from sqlalchemy import select
        from app.models.entity_revision import EntityRevision
        from app.models.user import User

        # Create a real user (FK constraint requires it)
        user = User(
            id=uuid4(),
            email="test-author@example.com",
            hashed_password="$2b$12$placeholder",
            is_active=True,
            is_superuser=False,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(user)
        await db_session.commit()

        service = EntityService(db_session)
        created = await service.create(
            EntityWrite(slug="pregabalin"),
            user_id=user.id,
        )

        result = await db_session.execute(
            select(EntityRevision)
            .where(EntityRevision.entity_id == created.id)
            .where(EntityRevision.is_current == True)
        )
        revision = result.scalar_one()
        assert revision.created_by_user_id == user.id

    async def test_create_duplicate_slug_rejected(self, db_session):
        """Test that creating two entities with the same slug is rejected."""
        # Arrange
        service = EntityService(db_session)
        entity_data = ScientificEntities.TRAMADOL
        await service.create(EntityWrite(slug=entity_data["slug"]))

        # Act & Assert - Attempting to create another entity with the same slug should fail
        with pytest.raises(HTTPException) as exc_info:
            await service.create(EntityWrite(slug=entity_data["slug"]))

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail.lower()

    async def test_update_entity_duplicate_slug_rejected(self, db_session):
        """Updating an entity to a slug already used by another entity returns 409."""
        service = EntityService(db_session)
        await service.create(EntityWrite(slug="ibuprofen"))
        second = await service.create(EntityWrite(slug="naproxen"))

        with pytest.raises(HTTPException) as exc_info:
            await service.update(second.id, EntityWrite(slug="ibuprofen"))

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail.lower()

    async def test_delete_entity_with_relations_rejected(self, db_session):
        """Deleting an entity referenced by a relation returns 409."""
        from app.models.source import Source
        from app.models.relation import Relation
        from app.models.relation_revision import RelationRevision
        from app.models.relation_role_revision import RelationRoleRevision

        service = EntityService(db_session)
        entity = await service.create(EntityWrite(slug="ketamine"))

        # Build minimal source → relation → revision → role chain
        source = Source()
        db_session.add(source)
        await db_session.flush()

        relation = Relation(source_id=source.id)
        db_session.add(relation)
        await db_session.flush()

        revision = RelationRevision(
            relation_id=relation.id,
            kind="treats",
            confidence=0.8,
            is_current=True,
        )
        db_session.add(revision)
        await db_session.flush()

        db_session.add(RelationRoleRevision(
            relation_revision_id=revision.id,
            entity_id=entity.id,
            role_type="target",
        ))
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await service.delete(entity.id)

        assert exc_info.value.status_code == 409
        assert "relation" in exc_info.value.detail.lower()

    async def test_update_marks_old_revision_as_not_current(self, db_session):
        """After update(), the previous revision must have is_current=False."""
        from sqlalchemy import select
        from app.models.entity_revision import EntityRevision

        service = EntityService(db_session)
        created = await service.create(EntityWrite(slug="metformin", summary={"en": "v1"}))
        await service.update(created.id, EntityWrite(slug="metformin", summary={"en": "v2"}))

        result = await db_session.execute(
            select(EntityRevision)
            .where(EntityRevision.entity_id == created.id)
            .order_by(EntityRevision.created_at)
        )
        revisions = result.scalars().all()

        assert len(revisions) == 2
        assert revisions[0].is_current is False
        assert revisions[0].summary == {"en": "v1"}
        assert revisions[1].is_current is True
        assert revisions[1].summary == {"en": "v2"}
