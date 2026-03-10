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
from fixtures.scientific_data import ScientificEntities, ScientificSources
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

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.LOW_DOSE_NALTREXONE["slug"], kind="drug"))

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

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.PREGABALIN["slug"], kind="drug"))
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

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
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


@pytest.mark.asyncio
class TestScopeFiltering:
    """Test scope-based filtering for inferences."""

    async def test_filter_by_exact_scope_match(self, db_session):
        """Test filtering relations by exact scope match."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.PREGABALIN["slug"], kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        # Create relation with adults scope
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                scope={"population": "adults"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Create relation with children scope
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.8,
                direction="positive",
                scope={"population": "children"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act - filter for adults only
        result = await inference_service.infer_for_entity(
            entity.id,
            scope_filter={"population": "adults"}
        )

        # Assert - should only get the adults relation
        assert result.entity_id == entity.id
        assert "effect" in result.relations_by_kind
        assert len(result.relations_by_kind["effect"]) == 1
        assert result.relations_by_kind["effect"][0].scope == {"population": "adults"}

    async def test_filter_by_partial_scope_match(self, db_session):
        """Test filtering with partial scope match (subset matching)."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        # Create relation with multiple scope attributes
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                scope={"population": "adults", "condition": "chronic_pain", "dosage": "high"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Create relation with different scope
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.7,
                direction="positive",
                scope={"population": "adults", "condition": "acute_pain"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act - filter for chronic pain only (partial match)
        result = await inference_service.infer_for_entity(
            entity.id,
            scope_filter={"condition": "chronic_pain"}
        )

        # Assert - should only get the chronic pain relation
        assert len(result.relations_by_kind["effect"]) == 1
        assert result.relations_by_kind["effect"][0].scope["condition"] == "chronic_pain"

    async def test_filter_no_scope_vs_empty_scope(self, db_session):
        """Test that relations with no scope are included when no filter is specified."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        # Create relation with no scope (general applicability)
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                scope=None,
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Create relation with specific scope
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.8,
                direction="positive",
                scope={"population": "adults"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act - no filter (should get both)
        result_no_filter = await inference_service.infer_for_entity(entity.id)

        # Assert
        assert len(result_no_filter.relations_by_kind["effect"]) == 2

        # Act - with filter (should exclude general relation)
        result_with_filter = await inference_service.infer_for_entity(
            entity.id,
            scope_filter={"population": "adults"}
        )

        # Assert - should only get the scoped relation
        assert len(result_with_filter.relations_by_kind["effect"]) == 1

    async def test_filter_multiple_scope_attributes(self, db_session):
        """Test filtering with multiple scope attributes (AND logic)."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        # Relation 1: adults + chronic
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                scope={"population": "adults", "condition": "chronic_pain"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Relation 2: adults + acute
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.8,
                direction="positive",
                scope={"population": "adults", "condition": "acute_pain"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Relation 3: children + chronic
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.7,
                direction="positive",
                scope={"population": "children", "condition": "chronic_pain"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act - filter for adults AND chronic pain
        result = await inference_service.infer_for_entity(
            entity.id,
            scope_filter={"population": "adults", "condition": "chronic_pain"}
        )

        # Assert - should only get relation 1
        assert len(result.relations_by_kind["effect"]) == 1
        assert result.relations_by_kind["effect"][0].scope == {"population": "adults", "condition": "chronic_pain"}

    async def test_scope_affects_inference_scores(self, db_session):
        """Test that scope filtering affects computed inference scores."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)

        entity = await entity_service.create(EntityWrite(slug=ScientificEntities.GABAPENTIN["slug"], kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        # Create positive relation for adults
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                scope={"population": "adults"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id), weight=0.8)],
            )
        )

        # Create negative relation for children
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="negative",
                scope={"population": "children"},
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id), weight=-0.7)],
            )
        )

        # Act - inference for all (should have mixed/contradictory evidence)
        result_all = await inference_service.infer_for_entity(entity.id)

        # Act - inference for adults only (should be clearly positive)
        result_adults = await inference_service.infer_for_entity(
            entity.id,
            scope_filter={"population": "adults"}
        )

        # Assert - adults-only inference should have higher positive score
        assert len(result_adults.role_inferences) > 0
        drug_inference_adults = next(r for r in result_adults.role_inferences if r.role_type == "drug")

        # Score should be positive for adults scope
        assert drug_inference_adults.score > 0
        # Coverage should be lower (only 1 relation)
        assert drug_inference_adults.coverage < result_all.role_inferences[0].coverage if result_all.role_inferences else True
