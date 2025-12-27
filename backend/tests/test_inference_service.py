"""
Tests for InferenceService.

Tests basic inference grouping logic (minimal implementation).
"""
import pytest
from uuid import uuid4

from app.services.inference_service import InferenceService
from app.services.entity_service import EntityService
from app.services.source_service import SourceService
from app.services.relation_service import RelationService
from app.schemas.entity import EntityWrite
from app.schemas.source import SourceWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite as RoleWrite


@pytest.mark.asyncio
class TestInferenceService:
    """Test InferenceService grouping logic."""

    async def test_infer_for_entity_no_relations(self, db_session):
        """Test inference for entity with no relations."""
        # Arrange
        entity_service = EntityService(db_session)
        inference_service = InferenceService(db_session)

        entity = await entity_service.create(EntityWrite(slug="orphan", kind="drug"))

        # Act
        result = await inference_service.infer_for_entity(entity.id)

        # Assert
        assert result.entity_id == entity.id
        assert result.relations_by_kind == {}

    async def test_infer_for_entity_single_kind(self, db_session):
        """Test inference groups relations by kind."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)

        entity = await entity_service.create(EntityWrite(slug="aspirin", kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        # Create two relations of same kind
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="negative",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await inference_service.infer_for_entity(entity.id)

        # Assert
        assert result.entity_id == entity.id
        assert "effect" in result.relations_by_kind
        assert len(result.relations_by_kind["effect"]) == 2

    async def test_infer_for_entity_multiple_kinds(self, db_session):
        """Test inference separates different relation kinds."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        # Create relations of different kinds
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="mechanism",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="contraindication",
                confidence=0.9,
                direction="negative",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act
        result = await inference_service.infer_for_entity(entity.id)

        # Assert
        assert result.entity_id == entity.id
        assert len(result.relations_by_kind) == 3
        assert "effect" in result.relations_by_kind
        assert "mechanism" in result.relations_by_kind
        assert "contraindication" in result.relations_by_kind
        assert len(result.relations_by_kind["effect"]) == 1
        assert len(result.relations_by_kind["mechanism"]) == 1
        assert len(result.relations_by_kind["contraindication"]) == 1

    async def test_infer_for_nonexistent_entity(self, db_session):
        """Test inference for non-existent entity returns empty."""
        # Arrange
        inference_service = InferenceService(db_session)
        fake_id = uuid4()

        # Act
        result = await inference_service.infer_for_entity(fake_id)

        # Assert
        assert result.entity_id == fake_id
        assert result.relations_by_kind == {}
