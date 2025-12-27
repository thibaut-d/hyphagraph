"""
Tests for RelationService.

Tests relation CRUD with role management and source_id immutability.
"""
import pytest
from uuid import uuid4
from fastapi import HTTPException

from app.services.relation_service import RelationService
from app.services.source_service import SourceService
from app.services.entity_service import EntityService
from app.schemas.relation import RelationWrite, RoleRevisionWrite as RoleWrite
from app.schemas.source import SourceWrite
from app.schemas.entity import EntityWrite


@pytest.mark.asyncio
class TestRelationService:
    """Test RelationService CRUD operations."""

    async def test_create_relation(self, db_session):
        """Test creating a relation with roles."""
        # Arrange
        source_service = SourceService(db_session)
        entity_service = EntityService(db_session)
        relation_service = RelationService(db_session)

        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/study"))
        entity = await entity_service.create(EntityWrite(slug="aspirin", kind="drug"))

        payload = RelationWrite(
            source_id=str(source.id),
            kind="effect",
            confidence=0.9,
            direction="positive",
            roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
        )

        # Act
        result = await relation_service.create(payload)

        # Assert
        assert result.kind == "effect"
        assert result.direction == "positive"
        assert result.source_id == source.id
        assert len(result.roles) == 1
        assert result.roles[0].role_type == "drug"

    async def test_create_relation_multiple_roles(self, db_session):
        """Test creating relation with multiple roles."""
        # Arrange
        source_service = SourceService(db_session)
        entity_service = EntityService(db_session)
        relation_service = RelationService(db_session)

        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/study"))
        drug = await entity_service.create(EntityWrite(slug="aspirin", kind="drug"))
        disease = await entity_service.create(EntityWrite(slug="pain", kind="symptom"))

        payload = RelationWrite(
            source_id=str(source.id),
            kind="treats",
            confidence=0.9,
            direction="positive",
            roles=[
                RoleWrite(role_type="drug", entity_id=str(drug.id)),
                RoleWrite(role_type="condition", entity_id=str(disease.id)),
            ],
        )

        # Act
        result = await relation_service.create(payload)

        # Assert
        assert len(result.roles) == 2
        role_names = {r.role_type for r in result.roles}
        assert role_names == {"drug", "condition"}

    async def test_get_relation(self, db_session):
        """Test retrieving a relation."""
        # Arrange
        source_service = SourceService(db_session)
        entity_service = EntityService(db_session)
        relation_service = RelationService(db_session)

        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/study"))
        entity = await entity_service.create(EntityWrite(slug="test", kind="drug"))

        created = await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await relation_service.get(created.id)

        # Assert
        assert result.id == created.id
        assert result.kind == "effect"

    async def test_get_relation_not_found(self, db_session):
        """Test getting non-existent relation raises 404."""
        # Arrange
        service = RelationService(db_session)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.get(uuid4())
        assert exc_info.value.status_code == 404

    async def test_list_by_source(self, db_session):
        """Test listing relations by source."""
        # Arrange
        source_service = SourceService(db_session)
        entity_service = EntityService(db_session)
        relation_service = RelationService(db_session)

        source1 = await source_service.create(SourceWrite(kind="study", title="Source 1", url="https://example.com/study"))
        source2 = await source_service.create(SourceWrite(kind="study", title="Source 2", url="https://example.com/study"))
        entity = await entity_service.create(EntityWrite(slug="test", kind="drug"))

        # Create relations for different sources
        await relation_service.create(
            RelationWrite(
                source_id=str(source1.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source1.id),
                kind="mechanism",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source2.id),
                kind="effect",
                confidence=0.9,
                direction="negative",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await relation_service.list_by_source(str(source1.id))

        # Assert
        assert len(result) == 2
        assert all(r.source_id == str(source1.id) for r in result)

    async def test_update_relation(self, db_session):
        """Test updating a relation."""
        # Arrange
        source_service = SourceService(db_session)
        entity_service = EntityService(db_session)
        relation_service = RelationService(db_session)

        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/study"))
        entity = await entity_service.create(EntityWrite(slug="test", kind="drug"))

        created = await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        updated = await relation_service.update(
            created.id,
            RelationWrite(
                source_id=str(source.id),  # Same source_id
                kind="mechanism",  # Changed
                direction="negative",  # Changed
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Assert
        assert updated.id == created.id
        assert updated.kind == "mechanism"
        assert updated.direction == "negative"

    async def test_update_relation_source_id_immutable(self, db_session):
        """Test that updating source_id raises error (immutable)."""
        # Arrange
        source_service = SourceService(db_session)
        entity_service = EntityService(db_session)
        relation_service = RelationService(db_session)

        source1 = await source_service.create(SourceWrite(kind="study", title="Source 1", url="https://example.com/study"))
        source2 = await source_service.create(SourceWrite(kind="study", title="Source 2", url="https://example.com/study"))
        entity = await entity_service.create(EntityWrite(slug="test", kind="drug"))

        created = await relation_service.create(
            RelationWrite(
                source_id=str(source1.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act & Assert - Attempting to change source_id should fail
        with pytest.raises(HTTPException) as exc_info:
            await relation_service.update(
                created.id,
                RelationWrite(
                    source_id=str(source2.id),  # Different source_id
                    kind="effect",
                    confidence=0.9,
                    direction="positive",
                    roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
                )
            )
        assert exc_info.value.status_code == 400
        assert "cannot change source_id" in exc_info.value.detail.lower()

    async def test_update_relation_not_found(self, db_session):
        """Test updating non-existent relation raises 404."""
        # Arrange
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/study"))

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await relation_service.update(
                uuid4(),
                RelationWrite(
                    source_id=str(source.id),
                    kind="effect",
                    confidence=0.9,
                    direction="positive",
                    roles=[],
                )
            )
        assert exc_info.value.status_code == 404

    async def test_delete_relation(self, db_session):
        """Test deleting a relation."""
        # Arrange
        source_service = SourceService(db_session)
        entity_service = EntityService(db_session)
        relation_service = RelationService(db_session)

        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/study"))
        entity = await entity_service.create(EntityWrite(slug="test", kind="drug"))

        created = await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        await relation_service.delete(created.id)

        # Assert
        with pytest.raises(HTTPException) as exc_info:
            await relation_service.get(created.id)
        assert exc_info.value.status_code == 404

    async def test_delete_relation_not_found(self, db_session):
        """Test deleting non-existent relation raises 404."""
        # Arrange
        service = RelationService(db_session)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.delete(uuid4())
        assert exc_info.value.status_code == 404
