from uuid import uuid4

import pytest

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.ui_category import UiCategory
from app.llm.schemas import ExtractedEntity
from app.services.entity_linking_service import (
    EntityLinkMatch,
    EntityLinkingService,
    ExactSlugMatch,
    SynonymMatch,
)


async def _create_entity_with_revision(
    db_session,
    *,
    slug: str,
    summary: str,
    category_id,
):
    entity = Entity()
    db_session.add(entity)
    await db_session.flush()
    db_session.add(
        EntityRevision(
            entity_id=entity.id,
            slug=slug,
            summary={"en": summary},
            ui_category_id=category_id,
            is_current=True,
        )
    )
    await db_session.flush()
    return entity


@pytest.fixture
async def ui_category(db_session):
    category = UiCategory(slug="test-category", labels={"en": "Test Category"}, order=1)
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest.mark.asyncio
class TestEntityLinkingService:
    async def test_find_exact_slug_match_returns_named_record(self, db_session, ui_category):
        entity = await _create_entity_with_revision(
            db_session,
            slug="aspirin",
            summary="Pain relief medication",
            category_id=ui_category.id,
        )
        await db_session.commit()

        service = EntityLinkingService(db_session)

        match = await service._find_exact_slug_match("aspirin")

        assert match == ExactSlugMatch(entity_id=entity.id, slug="aspirin")

    async def test_find_synonym_match_returns_named_record(self, db_session, ui_category):
        entity = await _create_entity_with_revision(
            db_session,
            slug="acetylsalicylic-acid",
            summary="Aspirin",
            category_id=ui_category.id,
        )
        db_session.add(
            EntityTerm(
                entity_id=entity.id,
                term="aspirin",
                language="en",
                display_order=1,
            )
        )
        await db_session.commit()

        service = EntityLinkingService(db_session)

        match = await service._find_synonym_match("aspirin")

        assert match == SynonymMatch(
            entity_id=entity.id,
            entity_slug="acetylsalicylic-acid",
        )

    async def test_filter_high_confidence_returns_slug_entity_mapping(self, db_session):
        exact_entity_id = uuid4()
        synonym_entity_id = uuid4()
        service = EntityLinkingService(db_session)

        auto_links = service.filter_high_confidence(
            [
                EntityLinkMatch(
                    extracted_slug="aspirin",
                    matched_entity_id=exact_entity_id,
                    matched_entity_slug="aspirin",
                    confidence=1.0,
                    match_type="exact",
                ),
                EntityLinkMatch(
                    extracted_slug="acetaminophen",
                    matched_entity_id=synonym_entity_id,
                    matched_entity_slug="paracetamol",
                    confidence=0.8,
                    match_type="synonym",
                ),
                EntityLinkMatch(
                    extracted_slug="ibuprofen",
                    matched_entity_id=None,
                    matched_entity_slug=None,
                    confidence=0.4,
                    match_type="none",
                ),
            ]
        )

        assert auto_links == {
            "aspirin": exact_entity_id,
            "acetaminophen": synonym_entity_id,
        }

    async def test_find_entity_matches_uses_named_lookup_records(self, db_session, ui_category):
        await _create_entity_with_revision(
            db_session,
            slug="aspirin",
            summary="Pain relief medication",
            category_id=ui_category.id,
        )
        synonym_entity = await _create_entity_with_revision(
            db_session,
            slug="acetylsalicylic-acid",
            summary="Aspirin synonym target",
            category_id=ui_category.id,
        )
        db_session.add(
            EntityTerm(
                entity_id=synonym_entity.id,
                term="asa",
                language="en",
                display_order=1,
            )
        )
        await db_session.commit()

        service = EntityLinkingService(db_session)

        matches = await service.find_entity_matches(
            [
                ExtractedEntity(
                    slug="aspirin",
                    summary="Aspirin summary",
                    category="drug",
                    confidence="high",
                    text_span="aspirin mention",
                ),
                ExtractedEntity(
                    slug="asa",
                    summary="ASA synonym summary",
                    category="drug",
                    confidence="medium",
                    text_span="asa mention",
                ),
                ExtractedEntity(
                    slug="unknown-entity",
                    summary="Unknown entity summary",
                    category="drug",
                    confidence="low",
                    text_span="unknown mention",
                ),
            ]
        )

        assert [match.match_type for match in matches] == ["exact", "synonym", "none"]
        assert matches[0].matched_entity_slug == "aspirin"
        assert matches[1].matched_entity_slug == "acetylsalicylic-acid"
        assert matches[2].matched_entity_id is None

    async def test_draft_entity_not_matched_by_exact_slug(self, db_session, ui_category):
        """Draft entities must not be matched by exact slug lookup (AUD29F-M1)."""
        entity = Entity()
        db_session.add(entity)
        await db_session.flush()
        db_session.add(EntityRevision(
            entity_id=entity.id,
            slug="draft-drug",
            ui_category_id=ui_category.id,
            status="draft",
            is_current=True,
        ))
        await db_session.commit()

        service = EntityLinkingService(db_session)
        match = await service._find_exact_slug_match("draft-drug")

        assert match is None

    async def test_draft_entity_not_matched_by_synonym(self, db_session, ui_category):
        """Draft entities must not be matched by synonym lookup (AUD29F-M1)."""
        entity = Entity()
        db_session.add(entity)
        await db_session.flush()
        db_session.add(EntityRevision(
            entity_id=entity.id,
            slug="draft-compound",
            ui_category_id=ui_category.id,
            status="draft",
            is_current=True,
        ))
        db_session.add(EntityTerm(
            entity_id=entity.id,
            term="draft-synonym",
            language="en",
            display_order=1,
        ))
        await db_session.commit()

        service = EntityLinkingService(db_session)
        match = await service._find_synonym_match("draft-synonym")

        assert match is None
