"""
Tests for inference read-model builders.

Covers:
- matches_scope: pure scope-matching predicate
- cache_computed_inference: persistence, direction derivation, idempotency, per-role storage
- convert_cached_to_inference_read: restoring InferenceRead from cached records
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from sqlalchemy import select

from app.config import settings
from app.models.computed_relation import ComputedRelation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.repositories.computed_relation_repo import ComputedRelationRepository
from app.repositories.relation_repo import RelationRepository
from app.schemas.inference import RoleInference
from app.services.inference.read_models import (
    cache_computed_inference,
    convert_cached_to_inference_read,
    matches_scope,
)
from app.models.entity import Entity
from app.utils.hashing import compute_scope_hash


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_entity(db) -> UUID:
    """Insert a bare Entity row and return its id."""
    from uuid import uuid4
    entity = Entity(id=uuid4())
    db.add(entity)
    await db.flush()
    return entity.id


def _make_role_inference(
    role_type: str,
    score: float,
    coverage: float = 1.0,
    disagreement: float = 0.0,
) -> RoleInference:
    return RoleInference(
        role_type=role_type,
        score=score,
        coverage=coverage,
        confidence=0.5,
        disagreement=disagreement,
    )


def _make_relation_mock(*, is_current: bool = True, scope=None):
    """Build a minimal mock Relation with one revision."""
    rev = MagicMock()
    rev.is_current = is_current
    rev.scope = scope
    rev.roles = []
    rel = MagicMock()
    rel.revisions = [rev]
    return rel


def _make_cached_role_rev(role_type, weight, coverage, disagreement=None):
    """Build a mock RelationRoleRevision-like object from the cache."""
    role_rev = MagicMock()
    role_rev.role_type = role_type
    role_rev.weight = weight
    role_rev.coverage = coverage
    role_rev.disagreement = disagreement
    return role_rev


def _make_cached_computed(role_revs, uncertainty=0.0):
    """Build a mock ComputedRelation with an attached Relation/RevisionRevision."""
    current_rev = MagicMock()
    current_rev.is_current = True
    current_rev.roles = role_revs
    relation = MagicMock()
    relation.revisions = [current_rev]
    cached = MagicMock()
    cached.relation = relation
    cached.uncertainty = uncertainty
    return cached


# ---------------------------------------------------------------------------
# matches_scope
# ---------------------------------------------------------------------------

class TestMatchesScope:
    def test_no_revisions_returns_false(self):
        rel = MagicMock()
        rel.revisions = []
        assert matches_scope(rel, {"kind": "study"}) is False

    def test_no_current_revision_returns_false(self):
        rev = MagicMock()
        rev.is_current = False
        rel = MagicMock()
        rel.revisions = [rev]
        assert matches_scope(rel, {"kind": "study"}) is False

    def test_current_revision_scope_is_none_returns_false(self):
        rel = _make_relation_mock(is_current=True, scope=None)
        assert matches_scope(rel, {"kind": "study"}) is False

    def test_all_keys_match_returns_true(self):
        rel = _make_relation_mock(is_current=True, scope={"population": "adults", "phase": "3"})
        assert matches_scope(rel, {"population": "adults"}) is True

    def test_one_key_mismatch_returns_false(self):
        rel = _make_relation_mock(is_current=True, scope={"population": "adults"})
        assert matches_scope(rel, {"population": "children"}) is False

    def test_key_absent_in_scope_returns_false(self):
        rel = _make_relation_mock(is_current=True, scope={"population": "adults"})
        assert matches_scope(rel, {"phase": "3"}) is False

    def test_empty_scope_filter_always_matches(self):
        rel = _make_relation_mock(is_current=True, scope={"population": "adults"})
        assert matches_scope(rel, {}) is True


# ---------------------------------------------------------------------------
# cache_computed_inference
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestCacheComputedInference:
    async def test_no_op_when_system_source_id_not_configured(self, db_session):
        """When SYSTEM_SOURCE_ID is empty, caching is silently skipped."""
        original = settings.SYSTEM_SOURCE_ID
        settings.SYSTEM_SOURCE_ID = ""
        try:
            computed_repo = ComputedRelationRepository(db_session)
            entity_id = await _create_entity(db_session)

            await cache_computed_inference(
                db=db_session,
                computed_repo=computed_repo,
                entity_id=entity_id,
                scope_filter=None,
                role_inferences=[_make_role_inference("subject", 1.0)],
            )

            scope_hash = compute_scope_hash(entity_id, None)
            result = await computed_repo.get_by_scope_hash(
                scope_hash, settings.INFERENCE_MODEL_VERSION
            )
            assert result is None
        finally:
            settings.SYSTEM_SOURCE_ID = original

    async def test_creates_computed_relation_row(self, db_session, system_source):
        """A ComputedRelation row with the correct scope_hash and model_version is created."""
        computed_repo = ComputedRelationRepository(db_session)
        entity_id = await _create_entity(db_session)

        await cache_computed_inference(
            db=db_session,
            computed_repo=computed_repo,
            entity_id=entity_id,
            scope_filter=None,
            role_inferences=[_make_role_inference("subject", 0.8, coverage=1.0)],
        )
        await db_session.commit()

        scope_hash = compute_scope_hash(entity_id, None)
        cached = await computed_repo.get_by_scope_hash(
            scope_hash, settings.INFERENCE_MODEL_VERSION
        )
        assert cached is not None
        assert cached.scope_hash == scope_hash
        assert cached.model_version == settings.INFERENCE_MODEL_VERSION

    async def test_idempotent_second_call_is_no_op(self, db_session, system_source):
        """Calling cache_computed_inference twice for the same entity does not raise and
        leaves exactly one ComputedRelation row."""
        computed_repo = ComputedRelationRepository(db_session)
        entity_id = await _create_entity(db_session)
        role_inferences = [_make_role_inference("subject", 1.0)]

        await cache_computed_inference(
            db=db_session,
            computed_repo=computed_repo,
            entity_id=entity_id,
            scope_filter=None,
            role_inferences=role_inferences,
        )
        await db_session.commit()

        # Second call should find the existing entry and return early
        await cache_computed_inference(
            db=db_session,
            computed_repo=computed_repo,
            entity_id=entity_id,
            scope_filter=None,
            role_inferences=role_inferences,
        )
        await db_session.commit()

        # Verify still only one entry
        scope_hash = compute_scope_hash(entity_id, None)
        result = await db_session.execute(
            select(ComputedRelation).where(ComputedRelation.scope_hash == scope_hash)
        )
        rows = result.scalars().all()
        assert len(rows) == 1

    async def test_positive_net_score_derives_positive_direction(self, db_session, system_source):
        """Net score > 0 → RelationRevision.direction stored as 'positive'."""
        computed_repo = ComputedRelationRepository(db_session)
        entity_id = await _create_entity(db_session)

        await cache_computed_inference(
            db=db_session,
            computed_repo=computed_repo,
            entity_id=entity_id,
            scope_filter=None,
            role_inferences=[_make_role_inference("subject", 0.9)],
        )
        await db_session.commit()

        scope_hash = compute_scope_hash(entity_id, None)
        cached = await computed_repo.get_by_scope_hash(
            scope_hash, settings.INFERENCE_MODEL_VERSION
        )
        result = await db_session.execute(
            select(RelationRevision).where(RelationRevision.relation_id == cached.relation_id)
        )
        revision = result.scalar_one()
        assert revision.direction == "positive"

    async def test_negative_net_score_derives_negative_direction(self, db_session, system_source):
        """Net score < 0 → RelationRevision.direction stored as 'negative'."""
        computed_repo = ComputedRelationRepository(db_session)
        entity_id = await _create_entity(db_session)

        await cache_computed_inference(
            db=db_session,
            computed_repo=computed_repo,
            entity_id=entity_id,
            scope_filter=None,
            role_inferences=[_make_role_inference("subject", -0.7)],
        )
        await db_session.commit()

        scope_hash = compute_scope_hash(entity_id, None)
        cached = await computed_repo.get_by_scope_hash(
            scope_hash, settings.INFERENCE_MODEL_VERSION
        )
        result = await db_session.execute(
            select(RelationRevision).where(RelationRevision.relation_id == cached.relation_id)
        )
        revision = result.scalar_one()
        assert revision.direction == "negative"

    async def test_per_role_disagreement_stored_in_role_revision(self, db_session, system_source):
        """Disagreement per role is persisted in RelationRoleRevision.disagreement."""
        computed_repo = ComputedRelationRepository(db_session)
        entity_id = await _create_entity(db_session)

        await cache_computed_inference(
            db=db_session,
            computed_repo=computed_repo,
            entity_id=entity_id,
            scope_filter=None,
            role_inferences=[_make_role_inference("subject", 0.5, coverage=2.0, disagreement=0.4)],
        )
        await db_session.commit()

        result = await db_session.execute(
            select(RelationRoleRevision).where(
                RelationRoleRevision.entity_id == entity_id,
                RelationRoleRevision.role_type == "subject",
            )
        )
        role_rev = result.scalar_one()
        assert role_rev.disagreement == pytest.approx(0.4)
        assert role_rev.coverage == pytest.approx(2.0)

    async def test_average_disagreement_stored_as_uncertainty(self, db_session, system_source):
        """Average disagreement across all roles is stored in ComputedRelation.uncertainty."""
        computed_repo = ComputedRelationRepository(db_session)
        entity_id = await _create_entity(db_session)

        await cache_computed_inference(
            db=db_session,
            computed_repo=computed_repo,
            entity_id=entity_id,
            scope_filter=None,
            role_inferences=[
                _make_role_inference("subject", 0.8, disagreement=0.2),
                _make_role_inference("object", 0.6, disagreement=0.6),
            ],
        )
        await db_session.commit()

        scope_hash = compute_scope_hash(entity_id, None)
        cached = await computed_repo.get_by_scope_hash(
            scope_hash, settings.INFERENCE_MODEL_VERSION
        )
        assert cached.uncertainty == pytest.approx(0.4)  # (0.2 + 0.6) / 2

    async def test_empty_role_inferences_stored_with_zero_uncertainty(self, db_session, system_source):
        """Empty role_inferences list results in uncertainty=0.0."""
        computed_repo = ComputedRelationRepository(db_session)
        entity_id = await _create_entity(db_session)

        await cache_computed_inference(
            db=db_session,
            computed_repo=computed_repo,
            entity_id=entity_id,
            scope_filter=None,
            role_inferences=[],
        )
        await db_session.commit()

        scope_hash = compute_scope_hash(entity_id, None)
        cached = await computed_repo.get_by_scope_hash(
            scope_hash, settings.INFERENCE_MODEL_VERSION
        )
        assert cached is not None
        assert cached.uncertainty == pytest.approx(0.0)

    async def test_scoped_and_unscoped_cache_entries_are_separate(self, db_session, system_source):
        """Different scope_filters produce different scope_hashes and separate cache entries."""
        computed_repo = ComputedRelationRepository(db_session)
        entity_id = await _create_entity(db_session)
        role_inferences = [_make_role_inference("subject", 0.5)]

        await cache_computed_inference(
            db=db_session,
            computed_repo=computed_repo,
            entity_id=entity_id,
            scope_filter=None,
            role_inferences=role_inferences,
        )
        await cache_computed_inference(
            db=db_session,
            computed_repo=computed_repo,
            entity_id=entity_id,
            scope_filter={"population": "adults"},
            role_inferences=role_inferences,
        )
        await db_session.commit()

        hash_none = compute_scope_hash(entity_id, None)
        hash_scoped = compute_scope_hash(entity_id, {"population": "adults"})
        assert hash_none != hash_scoped

        cached_none = await computed_repo.get_by_scope_hash(hash_none, settings.INFERENCE_MODEL_VERSION)
        cached_scoped = await computed_repo.get_by_scope_hash(
            hash_scoped, settings.INFERENCE_MODEL_VERSION
        )
        assert cached_none is not None
        assert cached_scoped is not None
        assert cached_none.relation_id != cached_scoped.relation_id


# ---------------------------------------------------------------------------
# convert_cached_to_inference_read
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestConvertCachedToInferenceRead:
    async def test_role_inferences_built_from_cached_roles(self, db_session):
        """Score, coverage, and disagreement from cached role revisions appear in the result."""
        entity_id = uuid4()
        role_revs = [_make_cached_role_rev("subject", weight=0.8, coverage=2.0, disagreement=0.1)]
        cached = _make_cached_computed(role_revs, uncertainty=0.1)

        repo = MagicMock(spec=RelationRepository)
        repo.list_by_entity = AsyncMock(return_value=[])

        result = await convert_cached_to_inference_read(
            db=db_session,
            repo=repo,
            entity_id=entity_id,
            cached_computed=cached,
            scope_filter=None,
        )

        assert result.entity_id == entity_id
        assert len(result.role_inferences) == 1
        ri = result.role_inferences[0]
        assert ri.role_type == "subject"
        assert ri.score == pytest.approx(0.8)
        assert ri.coverage == pytest.approx(2.0)
        assert ri.disagreement == pytest.approx(0.1)

    async def test_confidence_derived_from_coverage(self, db_session):
        """Confidence is re-computed from coverage, not read from cache."""
        entity_id = uuid4()
        role_revs = [_make_cached_role_rev("subject", weight=0.9, coverage=5.0, disagreement=0.0)]
        cached = _make_cached_computed(role_revs, uncertainty=0.0)

        repo = MagicMock(spec=RelationRepository)
        repo.list_by_entity = AsyncMock(return_value=[])

        result = await convert_cached_to_inference_read(
            db=db_session,
            repo=repo,
            entity_id=entity_id,
            cached_computed=cached,
            scope_filter=None,
        )

        ri = result.role_inferences[0]
        assert 0 < ri.confidence <= 1

    async def test_falls_back_to_global_uncertainty_when_role_disagreement_is_none(
        self, db_session
    ):
        """Pre-migration rows with role_rev.disagreement=None fall back to cached_computed.uncertainty."""
        entity_id = uuid4()
        role_revs = [_make_cached_role_rev("subject", weight=0.5, coverage=1.0, disagreement=None)]
        cached = _make_cached_computed(role_revs, uncertainty=0.35)

        repo = MagicMock(spec=RelationRepository)
        repo.list_by_entity = AsyncMock(return_value=[])

        result = await convert_cached_to_inference_read(
            db=db_session,
            repo=repo,
            entity_id=entity_id,
            cached_computed=cached,
            scope_filter=None,
        )

        ri = result.role_inferences[0]
        assert ri.disagreement == pytest.approx(0.35)

    async def test_empty_cached_roles_produces_empty_role_inferences(self, db_session):
        """A cached record with no roles results in an empty role_inferences list."""
        entity_id = uuid4()
        cached = _make_cached_computed(role_revs=[], uncertainty=0.0)

        repo = MagicMock(spec=RelationRepository)
        repo.list_by_entity = AsyncMock(return_value=[])

        result = await convert_cached_to_inference_read(
            db=db_session,
            repo=repo,
            entity_id=entity_id,
            cached_computed=cached,
            scope_filter=None,
        )

        assert result.entity_id == entity_id
        assert result.role_inferences == []
        assert result.relations_by_kind == {}

    async def test_multiple_roles_all_appear_in_result(self, db_session):
        """Multiple cached role revisions each produce a separate RoleInference."""
        entity_id = uuid4()
        role_revs = [
            _make_cached_role_rev("subject", weight=0.9, coverage=2.0, disagreement=0.1),
            _make_cached_role_rev("object", weight=-0.3, coverage=1.0, disagreement=0.7),
        ]
        cached = _make_cached_computed(role_revs, uncertainty=0.4)

        repo = MagicMock(spec=RelationRepository)
        repo.list_by_entity = AsyncMock(return_value=[])

        result = await convert_cached_to_inference_read(
            db=db_session,
            repo=repo,
            entity_id=entity_id,
            cached_computed=cached,
            scope_filter=None,
        )

        assert len(result.role_inferences) == 2
        role_types = {ri.role_type for ri in result.role_inferences}
        assert role_types == {"subject", "object"}

    async def test_live_relations_fetched_via_repo(self, db_session):
        """repo.list_by_entity is called with the correct entity_id."""
        entity_id = uuid4()
        cached = _make_cached_computed(role_revs=[], uncertainty=0.0)

        repo = MagicMock(spec=RelationRepository)
        repo.list_by_entity = AsyncMock(return_value=[])

        await convert_cached_to_inference_read(
            db=db_session,
            repo=repo,
            entity_id=entity_id,
            cached_computed=cached,
            scope_filter=None,
        )

        repo.list_by_entity.assert_called_once_with(entity_id)
