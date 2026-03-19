import pytest

from app.models.entity_term import EntityTerm
from app.schemas.entity import EntityWrite
from app.services.entity_merge_service import EntityMergeService
from app.services.entity_service import EntityService


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
