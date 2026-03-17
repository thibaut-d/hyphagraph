"""
Focused tests for revision_helpers.py single-current invariant.

The create_new_revision function must ensure that exactly one revision per
parent entity has is_current=True at all times.
"""
import pytest
from uuid import uuid4

from sqlalchemy import select

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.utils.revision_helpers import create_new_revision, get_current_revision


@pytest.mark.asyncio
class TestSingleCurrentInvariant:
    """create_new_revision must maintain exactly one is_current=True per parent."""

    async def _make_entity(self, db):
        entity = Entity()
        db.add(entity)
        await db.flush()
        return entity

    async def test_first_revision_is_current(self, db_session):
        entity = await self._make_entity(db_session)

        rev = await create_new_revision(
            db_session,
            EntityRevision,
            "entity_id",
            entity.id,
            {"slug": "first"},
        )

        assert rev.is_current is True

    async def test_second_revision_demotes_first(self, db_session):
        entity = await self._make_entity(db_session)

        rev1 = await create_new_revision(
            db_session,
            EntityRevision,
            "entity_id",
            entity.id,
            {"slug": "first"},
        )
        rev2 = await create_new_revision(
            db_session,
            EntityRevision,
            "entity_id",
            entity.id,
            {"slug": "second"},
        )

        await db_session.refresh(rev1)
        assert rev1.is_current is False
        assert rev2.is_current is True

    async def test_exactly_one_current_after_multiple_revisions(self, db_session):
        entity = await self._make_entity(db_session)

        for slug in ("a", "b", "c", "d"):
            await create_new_revision(
                db_session,
                EntityRevision,
                "entity_id",
                entity.id,
                {"slug": slug},
            )

        result = await db_session.execute(
            select(EntityRevision).where(
                EntityRevision.entity_id == entity.id,
                EntityRevision.is_current == True,  # noqa: E712
            )
        )
        current_revisions = result.scalars().all()

        assert len(current_revisions) == 1
        assert current_revisions[0].slug == "d"

    async def test_invariant_independent_across_entities(self, db_session):
        """Demoting revisions for entity A must not affect entity B."""
        entity_a = await self._make_entity(db_session)
        entity_b = await self._make_entity(db_session)

        await create_new_revision(
            db_session, EntityRevision, "entity_id", entity_a.id, {"slug": "a-first"}
        )
        await create_new_revision(
            db_session, EntityRevision, "entity_id", entity_b.id, {"slug": "b-first"}
        )
        await create_new_revision(
            db_session, EntityRevision, "entity_id", entity_a.id, {"slug": "a-second"}
        )

        b_current = await get_current_revision(
            db_session, EntityRevision, "entity_id", entity_b.id
        )
        assert b_current is not None
        assert b_current.slug == "b-first"

    async def test_set_as_current_false_leaves_no_current(self, db_session):
        """set_as_current=False must not touch existing revisions."""
        entity = await self._make_entity(db_session)

        rev1 = await create_new_revision(
            db_session,
            EntityRevision,
            "entity_id",
            entity.id,
            {"slug": "first"},
        )
        rev2 = await create_new_revision(
            db_session,
            EntityRevision,
            "entity_id",
            entity.id,
            {"slug": "draft"},
            set_as_current=False,
        )

        await db_session.refresh(rev1)
        assert rev1.is_current is True
        assert rev2.is_current is False
