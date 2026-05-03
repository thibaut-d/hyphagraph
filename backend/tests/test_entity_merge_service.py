import pytest
from sqlalchemy import select

from app.models.computed_relation import ComputedRelation
from app.models.entity_term import EntityTerm
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.schemas.entity import EntityWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite
from app.schemas.source import SourceWrite
from app.services.entity_merge_service import EntityMergeService
from app.services.entity_service import EntityService
from app.services.relation_service import RelationService
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
            {left_id, right_id} == {entity_one.id, entity_two.id}
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

    async def test_list_merge_candidates_returns_reviewable_entities(self, db_session):
        entity_service = EntityService(db_session)
        merge_service = EntityMergeService(db_session)

        source = await entity_service.create(
            EntityWrite(slug="fibromyalgia-syndrome", summary={"en": "Longer duplicate"})
        )
        target = await entity_service.create(
            EntityWrite(slug="fibromyalgia", summary={"en": "Canonical entity"})
        )

        candidates = await merge_service.list_merge_candidates(similarity_threshold=0.7)

        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.source.id == source.id
        assert candidate.source.slug == "fibromyalgia-syndrome"
        assert candidate.target.id == target.id
        assert candidate.target.slug == "fibromyalgia"
        assert candidate.similarity > 0.7
        assert candidate.reason == "One slug contains the other"
        assert candidate.score_factors["slug_similarity"] < round(candidate.similarity, 4)
        assert candidate.score_factors["contains_slug"] is True
        assert candidate.score_factors["both_have_summary"] is True

    async def test_list_merge_candidates_scores_terms_summaries_neighborhoods_and_sources(self, db_session):
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        merge_service = EntityMergeService(db_session)

        source = await entity_service.create(
            EntityWrite(
                slug="acetylsalicylic-acid",
                summary={"en": "A salicylate analgesic used for pain and inflammation."},
            )
        )
        target = await entity_service.create(
            EntityWrite(
                slug="aspirin",
                summary={"en": "A salicylate medicine used for pain and inflammation."},
            )
        )
        condition = await entity_service.create(EntityWrite(slug="headache"))
        evidence_source = await source_service.create(
            SourceWrite(kind="study", title="Aspirin duplicate context", url="https://example.com/aspirin-context")
        )
        db_session.add(
            EntityTerm(
                entity_id=source.id,
                term="aspirin",
                language="en",
                display_order=0,
            )
        )
        await db_session.commit()

        for entity in (source, target):
            await relation_service.create(
                RelationWrite(
                    source_id=evidence_source.id,
                    kind="treats",
                    direction="supports",
                    confidence=0.8,
                    roles=[
                        RoleRevisionWrite(entity_id=entity.id, role_type="agent"),
                        RoleRevisionWrite(entity_id=condition.id, role_type="target"),
                    ],
                )
            )

        candidates = await merge_service.list_merge_candidates(similarity_threshold=0.99)

        candidate = next(
            item
            for item in candidates
            if {item.source.id, item.target.id} == {source.id, target.id}
        )
        assert candidate.reason == "Exact or alias-level term match"
        assert candidate.similarity == 1.0
        assert candidate.score_factors["term_similarity"] == 1.0
        assert candidate.score_factors["summary_token_overlap"] > 0
        assert candidate.score_factors["shared_relation_neighbors"] == 1
        assert candidate.score_factors["shared_sources"] == 1

    async def test_circular_merge_is_rejected(self, db_session):
        """merge_entities raises ValueError when a reverse merge already exists (A→B then B→A)."""
        entity_service = EntityService(db_session)
        merge_service = EntityMergeService(db_session)

        entity_a = await entity_service.create(EntityWrite(slug="entity-circ-a"))
        entity_b = await entity_service.create(EntityWrite(slug="entity-circ-b"))

        # First merge: A → B (succeeds)
        await merge_service.merge_entities(entity_a.id, entity_b.id)

        # Second merge: B → A (must raise — circular)
        with pytest.raises(ValueError, match="[Cc]ircular"):
            await merge_service.merge_entities(entity_b.id, entity_a.id)

    async def test_merge_entities_deduplicates_current_relation_participants(self, db_session):
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        merge_service = EntityMergeService(db_session)

        source_entity = await entity_service.create(EntityWrite(slug="drug-source"))
        target_entity = await entity_service.create(EntityWrite(slug="drug-target"))
        condition_entity = await entity_service.create(EntityWrite(slug="condition"))
        source = await source_service.create(
            SourceWrite(kind="study", title="T", url="https://example.com/t1")
        )

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

        db_session.add_all(
            [
                RelationRoleRevision(
                    relation_revision_id=revision.id,
                    entity_id=source_entity.id,
                    role_type="agent",
                ),
                RelationRoleRevision(
                    relation_revision_id=revision.id,
                    entity_id=target_entity.id,
                    role_type="agent",
                ),
                RelationRoleRevision(
                    relation_revision_id=revision.id,
                    entity_id=condition_entity.id,
                    role_type="condition",
                ),
            ]
        )
        await db_session.commit()

        await merge_service.merge_entities(source_entity.id, target_entity.id)

        roles = (
            await db_session.execute(
                select(RelationRoleRevision).where(
                    RelationRoleRevision.relation_revision_id == revision.id
                )
            )
        ).scalars().all()

        agent_roles = [role for role in roles if role.role_type == "agent"]
        assert len(agent_roles) == 1
        assert agent_roles[0].entity_id == target_entity.id
