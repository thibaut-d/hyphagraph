"""
Tests for computed inference caching.

Tests the caching layer of the inference service:
- Cache hit/miss behavior
- Scope hash-based lookup
- Model version handling
"""
import pytest
from uuid import uuid4

from app.services.inference_service import InferenceService
from app.services.entity_service import EntityService
from app.services.source_service import SourceService
from app.services.relation_service import RelationService
from app.repositories.computed_relation_repo import ComputedRelationRepository
from app.schemas.entity import EntityWrite
from app.schemas.source import SourceWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite as RoleWrite
from app.config import settings


@pytest.mark.asyncio
class TestInferenceCaching:
    """Test caching behavior of inference service."""

    async def test_cache_miss_first_computation(self, db_session, system_source):
        """Test first computation creates cache entry."""

        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)
        computed_repo = ComputedRelationRepository(db_session)

        entity = await entity_service.create(EntityWrite(slug="aspirin", kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id), weight=0.8)],
            )
        )

        # Verify no cache entry exists initially
        from app.utils.hashing import compute_scope_hash
        scope_hash = compute_scope_hash(entity.id, None)
        cached_before = await computed_repo.get_by_scope_hash(scope_hash, settings.INFERENCE_MODEL_VERSION)
        assert cached_before is None

        # Act - first computation (cache miss)
        result = await inference_service.infer_for_entity(entity.id, use_cache=True)

        # Assert - result computed
        assert result.entity_id == entity.id
        assert len(result.role_inferences) > 0

        # Verify cache entry was created
        await db_session.commit()  # Ensure flush
        cached_after = await computed_repo.get_by_scope_hash(scope_hash, settings.INFERENCE_MODEL_VERSION)
        assert cached_after is not None
        assert cached_after.scope_hash == scope_hash

    async def test_cache_disabled_no_storage(self, db_session):
        """Test computation with cache disabled doesn't store."""
        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)
        computed_repo = ComputedRelationRepository(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Act - compute with cache disabled
        result = await inference_service.infer_for_entity(entity.id, use_cache=False)

        # Assert - result computed
        assert result.entity_id == entity.id

        # Verify no cache entry created
        from app.utils.hashing import compute_scope_hash
        scope_hash = compute_scope_hash(entity.id, None)
        cached = await computed_repo.get_by_scope_hash(scope_hash, settings.INFERENCE_MODEL_VERSION)
        assert cached is None

    async def test_different_scopes_different_cache(self, db_session, system_source):
        """Test different scope filters create separate cache entries."""

        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)
        computed_repo = ComputedRelationRepository(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        # Create relations with different scopes
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

        # Act - compute for adults scope
        result_adults = await inference_service.infer_for_entity(
            entity.id,
            scope_filter={"population": "adults"},
            use_cache=True
        )

        # Act - compute for children scope
        result_children = await inference_service.infer_for_entity(
            entity.id,
            scope_filter={"population": "children"},
            use_cache=True
        )

        # Assert - both computed
        assert result_adults.entity_id == entity.id
        assert result_children.entity_id == entity.id

        # Verify separate cache entries
        from app.utils.hashing import compute_scope_hash
        scope_hash_adults = compute_scope_hash(entity.id, {"population": "adults"})
        scope_hash_children = compute_scope_hash(entity.id, {"population": "children"})

        assert scope_hash_adults != scope_hash_children

        await db_session.commit()
        cached_adults = await computed_repo.get_by_scope_hash(scope_hash_adults, settings.INFERENCE_MODEL_VERSION)
        cached_children = await computed_repo.get_by_scope_hash(scope_hash_children, settings.INFERENCE_MODEL_VERSION)

        assert cached_adults is not None
        assert cached_children is not None
        assert cached_adults.relation_id != cached_children.relation_id

    async def test_uncertainty_from_disagreement(self, db_session, system_source):
        """Test uncertainty is computed from disagreement measure."""

        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)
        computed_repo = ComputedRelationRepository(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        # Create contradictory relations
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id), weight=0.8)],
            )
        )
        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="negative",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id), weight=-0.7)],
            )
        )

        # Act
        result = await inference_service.infer_for_entity(entity.id, use_cache=True)

        # Assert - disagreement should be captured
        drug_inference = next(r for r in result.role_inferences if r.role_type == "drug")
        assert drug_inference.disagreement > 0  # Should have some disagreement

        # Verify uncertainty is stored in cache
        from app.utils.hashing import compute_scope_hash
        scope_hash = compute_scope_hash(entity.id, None)
        await db_session.commit()
        cached = await computed_repo.get_by_scope_hash(scope_hash, settings.INFERENCE_MODEL_VERSION)

        assert cached is not None
        assert cached.uncertainty > 0  # Should reflect disagreement
        assert cached.uncertainty == drug_inference.disagreement  # Should match


@pytest.mark.asyncio
class TestCacheInvalidation:
    """Test cache invalidation scenarios."""

    async def test_delete_cache_by_scope_hash(self, db_session, system_source):
        """Test manual cache invalidation by scope hash."""

        # Arrange
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        inference_service = InferenceService(db_session)
        computed_repo = ComputedRelationRepository(db_session)

        entity = await entity_service.create(EntityWrite(slug="drug", kind="drug"))
        source = await source_service.create(SourceWrite(kind="study", title="Test", url="https://example.com/test"))

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.9,
                direction="positive",
                roles=[RoleWrite(role_type="drug", entity_id=str(entity.id))],
            )
        )

        # Create cache entry
        await inference_service.infer_for_entity(entity.id, use_cache=True)
        await db_session.commit()

        # Verify cache exists
        from app.utils.hashing import compute_scope_hash
        scope_hash = compute_scope_hash(entity.id, None)
        cached_before = await computed_repo.get_by_scope_hash(scope_hash, settings.INFERENCE_MODEL_VERSION)
        assert cached_before is not None

        # Act - invalidate cache
        await computed_repo.delete_by_scope_hash(scope_hash)
        await db_session.commit()

        # Assert - cache removed
        cached_after = await computed_repo.get_by_scope_hash(scope_hash, settings.INFERENCE_MODEL_VERSION)
        assert cached_after is None
