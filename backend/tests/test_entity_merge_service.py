import pytest
from sqlalchemy import select

from app.models.computed_relation import ComputedRelation
from app.models.entity_term import EntityTerm
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.schemas.entity import EntityWrite
from app.schemas.source import SourceWrite
from app.services.entity_merge_service import EntityMergeService
from app.services.entity_service import EntityService
from app.services.source_service import SourceService


@pytest.mark.asyncio
class TestEntityMergeService:
    async def test_find_potential_duplicates_detects_similar_slugs(self, db_session):
        entity_service = EntityService(db_session)
        merge_service = EntityMergeService(db_session)

        entity_one = await entity_service.create(EntityWrite(slug="aspirin"))
        entity_two = await entity_service.create(EntityWrite(slug="aspirine"))

        duplicates = await merge_service.find_potential_duplicates(similarity_threshold=0.8)

        assert any(
            left_id == entity_one.id
            and right_id == entity_two.id
            and similarity == pytest.approx(0.9333333333)
            for left_id, right_id, similarity in duplicates
        )

    async def test_find_potential_duplicates_detects_term_matches(self, db_session):
        entity_service = EntityService(db_session)
        merge_service = EntityMergeService(db_session)

        source_entity = await entity_service.create(EntityWrite(slug="aspirin"))
        target_entity = await entity_service.create(EntityWrite(slug="acetylsalicylic-acid"))
        db_session.add(
            EntityTerm(
                entity_id=target_entity.id,
                term="aspirin",
                language="en",
                display_order=0,
            )
        )
        await db_session.commit()

        duplicates = await merge_service.find_potential_duplicates(similarity_threshold=0.99)

        assert (source_entity.id, target_entity.id, 1.0) in duplicates

    async def test_merge_entities_invalidates_inference_cache(self, db_session):
        """merge_entities deletes ComputedRelation cache entries for both entities (DF-MRG-M2)."""
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        merge_service = EntityMergeService(db_session)

        source_entity = await entity_service.create(EntityWrite(slug="drug-source"))
        target_entity = await entity_service.create(EntityWrite(slug="drug-target"))
        source = await source_service.create(SourceWrite(kind="study", title="T", url="https://example.com/t1"))

        # Build a Relation whose current revision has a role pointing to target_entity,
        # then seed a ComputedRelation for it (simulating a cached inference).
        relation = Relation(source_id=source.id)
        db_session.add(relation)
        await db_session.flush()

        revision = RelationRevision(
            relation_id=relation.id,
            kind="treats",
            confidence=0.8,
            is_current=True,
            status="confirmed",
        )
        db_session.add(revision)
        await db_session.flush()

        db_session.add(RelationRoleRevision(
            relation_revision_id=revision.id,
            entity_id=target_entity.id,
            role_type="agent",
        ))

        cached = ComputedRelation(
            relation_id=relation.id,
            scope_hash="test-hash-target",
            model_version="v1",
            uncertainty=0.1,
        )
        db_session.add(cached)
        await db_session.commit()

        # Verify the cache entry exists
        result = await db_session.execute(
            select(ComputedRelation).where(ComputedRelation.relation_id == relation.id)
        )
        assert result.scalar_one_or_none() is not None

        # Merge — should invalidate the cache
        await merge_service.merge_entities(source_entity.id, target_entity.id)

        result = await db_session.execute(
            select(ComputedRelation).where(ComputedRelation.relation_id == relation.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_auto_merge_obvious_duplicates_dry_run_prefers_shorter_slug(self, db_session):
        entity_service = EntityService(db_session)
        merge_service = EntityMergeService(db_session)

        await entity_service.create(EntityWrite(slug="fibromyalgia-a"))
        await entity_service.create(EntityWrite(slug="fibromyalgia"))

        actions = await merge_service.auto_merge_obvious_duplicates(dry_run=True)

        assert len(actions) == 1
        assert actions[0].action == "merge"
        assert actions[0].source_slug == "fibromyalgia-a"
        assert actions[0].target_slug == "fibromyalgia"
