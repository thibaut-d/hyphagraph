"""
Regression tests for AUD29F-C1: draft revisions must not leak into public read paths.

Tests verify that entity/source/relation list and detail endpoints return only
confirmed revisions, and that drafts (LLM-created, pending review) are invisible
to user-facing queries.
"""
import pytest
from uuid import uuid4
from fastapi import HTTPException

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.services.entity_service import EntityService
from app.services.source_service import SourceService
from app.services.relation_service import RelationService
from app.schemas.entity import EntityWrite
from app.schemas.source import SourceWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite as RoleWrite
from app.schemas.filters import EntityFilters, SourceFilters


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _insert_draft_entity(db, slug: str) -> Entity:
    """Insert an entity whose current revision has status='draft'."""
    entity = Entity()
    db.add(entity)
    await db.flush()
    revision = EntityRevision(
        entity_id=entity.id,
        slug=slug,
        status="draft",
        is_current=True,
    )
    db.add(revision)
    await db.commit()
    return entity


async def _insert_draft_source(db, title: str) -> Source:
    """Insert a source whose current revision has status='draft'."""
    source = Source()
    db.add(source)
    await db.flush()
    revision = SourceRevision(
        source_id=source.id,
        kind="study",
        title=title,
        url="https://example.com/draft",
        status="draft",
        is_current=True,
    )
    db.add(revision)
    await db.commit()
    return source


async def _insert_draft_relation(db, source_id, entity_id) -> Relation:
    """Insert a relation whose current revision has status='draft'."""
    relation = Relation(source_id=source_id)
    db.add(relation)
    await db.flush()
    revision = RelationRevision(
        relation_id=relation.id,
        kind="effect",
        direction="supports",
        confidence=0.8,
        status="draft",
        is_current=True,
    )
    db.add(revision)
    await db.flush()
    role = RelationRoleRevision(
        relation_revision_id=revision.id,
        entity_id=entity_id,
        role_type="agent",
    )
    db.add(role)
    await db.commit()
    return relation


# ---------------------------------------------------------------------------
# Entity draft isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestEntityDraftIsolation:

    async def test_draft_entity_excluded_from_list(self, db_session):
        """Draft entities must not appear in the public entity list."""
        service = EntityService(db_session)
        # Confirmed entity
        confirmed = await service.create(EntityWrite(slug="confirmed-entity"))
        # Draft entity (bypassing service to set status=draft directly)
        await _insert_draft_entity(db_session, "draft-entity")

        items, total = await service.list_all()

        slugs = {e.slug for e in items}
        assert "confirmed-entity" in slugs
        assert "draft-entity" not in slugs
        assert total == 1

    async def test_draft_entity_not_found_on_get(self, db_session):
        """Getting a draft entity by ID must return 404."""
        service = EntityService(db_session)
        draft = await _insert_draft_entity(db_session, "draft-get-entity")

        with pytest.raises(HTTPException) as exc_info:
            await service.get(draft.id)

        assert exc_info.value.status_code == 404

    async def test_confirmed_entity_visible_on_get(self, db_session):
        """Confirmed entities remain accessible by ID."""
        service = EntityService(db_session)
        confirmed = await service.create(EntityWrite(slug="visible-entity"))

        result = await service.get(confirmed.id)

        assert result.slug == "visible-entity"

    async def test_draft_entity_excluded_from_filtered_list(self, db_session):
        """Draft entities are excluded even when filters are applied."""
        service = EntityService(db_session)
        await service.create(EntityWrite(slug="confirmed-filtered"))
        await _insert_draft_entity(db_session, "draft-filtered")

        filters = EntityFilters(search="filtered")
        items, total = await service.list_all(filters=filters)

        slugs = {e.slug for e in items}
        assert "confirmed-filtered" in slugs
        assert "draft-filtered" not in slugs


# ---------------------------------------------------------------------------
# Source draft isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestSourceDraftIsolation:

    async def test_draft_source_excluded_from_list(self, db_session):
        """Draft sources must not appear in the public source list."""
        service = SourceService(db_session)
        await service.create(SourceWrite(kind="study", title="Confirmed Source", url="https://example.com/confirmed"))
        await _insert_draft_source(db_session, "Draft Source")

        items, total = await service.list_all()

        titles = {s.title for s in items}
        assert "Confirmed Source" in titles
        assert "Draft Source" not in titles
        assert total == 1

    async def test_draft_source_not_found_on_get(self, db_session):
        """Getting a draft source by ID must return 404."""
        service = SourceService(db_session)
        draft = await _insert_draft_source(db_session, "Draft Get Source")

        with pytest.raises(HTTPException) as exc_info:
            await service.get(draft.id)

        assert exc_info.value.status_code == 404

    async def test_confirmed_source_visible_on_get(self, db_session):
        """Confirmed sources remain accessible by ID."""
        service = SourceService(db_session)
        confirmed = await service.create(
            SourceWrite(kind="review", title="Visible Source", url="https://example.com/visible")
        )

        result = await service.get(confirmed.id)

        assert result.title == "Visible Source"

    async def test_draft_source_excluded_from_search(self, db_session):
        """Draft sources are excluded even when a search filter matches them."""
        service = SourceService(db_session)
        await service.create(SourceWrite(kind="study", title="Confirmed Draft-Like Title", url="https://example.com/c"))
        await _insert_draft_source(db_session, "Draft-Like Title")

        filters = SourceFilters(search="Draft-Like")
        items, total = await service.list_all(filters=filters)

        titles = {s.title for s in items}
        assert "Confirmed Draft-Like Title" in titles
        assert "Draft-Like Title" not in titles


# ---------------------------------------------------------------------------
# Relation draft isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestRelationDraftIsolation:

    async def _setup(self, db_session):
        source_svc = SourceService(db_session)
        entity_svc = EntityService(db_session)
        source = await source_svc.create(
            SourceWrite(kind="study", title="Rel Test Source", url="https://example.com/rel")
        )
        entity1 = await entity_svc.create(EntityWrite(slug="rel-test-entity-a"))
        entity2 = await entity_svc.create(EntityWrite(slug="rel-test-entity-b"))
        return source, entity1, entity2

    async def test_draft_relation_excluded_from_list_by_source(self, db_session):
        """Draft relations must not appear when listing by source."""
        source, entity1, entity2 = await self._setup(db_session)
        relation_svc = RelationService(db_session)

        # Confirmed relation (requires ≥2 roles)
        confirmed = await relation_svc.create(RelationWrite(
            source_id=str(source.id),
            kind="effect",
            direction="supports",
            confidence=0.9,
            roles=[
                RoleWrite(role_type="agent", entity_id=str(entity1.id)),
                RoleWrite(role_type="target", entity_id=str(entity2.id)),
            ],
        ))
        # Draft relation (inserted directly to bypass service validation)
        await _insert_draft_relation(db_session, source.id, entity1.id)

        results = await relation_svc.list_by_source(source.id)

        assert len(results) == 1
        assert results[0].id == confirmed.id

    async def test_draft_relation_not_found_on_get(self, db_session):
        """Getting a draft relation by ID must return 404."""
        source, entity1, entity2 = await self._setup(db_session)
        draft = await _insert_draft_relation(db_session, source.id, entity1.id)
        service = RelationService(db_session)

        with pytest.raises(HTTPException) as exc_info:
            await service.get(draft.id)

        assert exc_info.value.status_code == 404

    async def test_confirmed_relation_visible_on_get(self, db_session):
        """Confirmed relations remain accessible by ID."""
        source, entity1, entity2 = await self._setup(db_session)
        service = RelationService(db_session)

        confirmed = await service.create(RelationWrite(
            source_id=str(source.id),
            kind="association",
            direction="supports",
            confidence=0.7,
            roles=[
                RoleWrite(role_type="agent", entity_id=str(entity1.id)),
                RoleWrite(role_type="target", entity_id=str(entity2.id)),
            ],
        ))

        result = await service.get(confirmed.id)
        assert result.id == confirmed.id
