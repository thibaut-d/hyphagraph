"""
Tests for RevisionReviewService.

Covers:
- list_drafts: returns only draft revisions, empty when none exist
- list_drafts: pagination and kind filter
- confirm: sets status='confirmed', returns False for unknown/non-draft
- discard: deletes the revision, returns False for unknown/non-draft
- get_draft_counts: per-kind + total counts
- bulk_creation_service sets status='draft' on LLM revisions
"""
import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.models.user import User
from app.services.revision_review_service import RevisionReviewService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_entity_revision(db: AsyncSession, status: str = "draft") -> EntityRevision:
    entity = Entity(id=uuid4())
    db.add(entity)
    await db.flush()

    rev = EntityRevision(
        entity_id=entity.id,
        slug=f"test-entity-{uuid4().hex[:6]}",
        created_with_llm="gpt-4",
        is_current=True,
        status=status,
    )
    db.add(rev)
    await db.flush()
    return rev


async def _make_relation_revision(db: AsyncSession, status: str = "draft") -> RelationRevision:
    source = Source()
    db.add(source)
    await db.flush()
    source_rev = SourceRevision(
        source_id=source.id,
        kind="study",
        title="Test Source",
        url="https://example.com",
        is_current=True,
        status="confirmed",
    )
    db.add(source_rev)
    await db.flush()

    relation = Relation(source_id=source.id)
    db.add(relation)
    await db.flush()

    rev = RelationRevision(
        relation_id=relation.id,
        kind="treats",
        created_with_llm="gpt-4",
        is_current=True,
        status=status,
    )
    db.add(rev)
    await db.flush()
    return rev


async def _make_source_revision(db: AsyncSession, status: str = "draft") -> SourceRevision:
    source = Source()
    db.add(source)
    await db.flush()

    rev = SourceRevision(
        source_id=source.id,
        kind="study",
        title=f"Draft Source {uuid4().hex[:6]}",
        url="https://example.com",
        created_with_llm="gpt-4",
        is_current=True,
        status=status,
    )
    db.add(rev)
    await db.flush()
    return rev


async def _make_reviewer(db: AsyncSession) -> User:
    reviewer = User(
        id=uuid4(),
        email=f"reviewer-{uuid4().hex[:6]}@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=True,
        is_verified=True,
    )
    db.add(reviewer)
    await db.flush()
    return reviewer


# ---------------------------------------------------------------------------
# list_drafts
# ---------------------------------------------------------------------------

class TestListDrafts:
    async def test_returns_empty_when_no_drafts(self, db_session: AsyncSession):
        svc = RevisionReviewService(db_session)
        result = await svc.list_drafts()
        assert result.items == []
        assert result.total == 0

    async def test_returns_entity_draft(self, db_session: AsyncSession):
        await _make_entity_revision(db_session, status="draft")
        svc = RevisionReviewService(db_session)
        result = await svc.list_drafts()
        assert result.total == 1
        assert result.items[0].revision_kind == "entity"

    async def test_does_not_return_confirmed_revisions(self, db_session: AsyncSession):
        await _make_entity_revision(db_session, status="confirmed")
        svc = RevisionReviewService(db_session)
        result = await svc.list_drafts()
        assert result.total == 0

    async def test_returns_all_kinds_mixed(self, db_session: AsyncSession):
        await _make_entity_revision(db_session)
        await _make_relation_revision(db_session)
        await _make_source_revision(db_session)
        svc = RevisionReviewService(db_session)
        result = await svc.list_drafts()
        assert result.total == 3
        kinds = {item.revision_kind for item in result.items}
        assert kinds == {"entity", "relation", "source"}

    async def test_kind_filter_entity(self, db_session: AsyncSession):
        await _make_entity_revision(db_session)
        await _make_relation_revision(db_session)
        svc = RevisionReviewService(db_session)
        result = await svc.list_drafts(revision_kind="entity")
        assert result.total == 1
        assert result.items[0].revision_kind == "entity"

    async def test_kind_filter_relation(self, db_session: AsyncSession):
        await _make_entity_revision(db_session)
        await _make_relation_revision(db_session)
        svc = RevisionReviewService(db_session)
        result = await svc.list_drafts(revision_kind="relation")
        assert result.total == 1
        assert result.items[0].revision_kind == "relation"

    async def test_pagination_page_size(self, db_session: AsyncSession):
        for _ in range(5):
            await _make_entity_revision(db_session)
        svc = RevisionReviewService(db_session)
        result = await svc.list_drafts(page=1, page_size=2)
        assert len(result.items) == 2
        assert result.total == 5
        assert result.has_more is True

    async def test_pagination_last_page(self, db_session: AsyncSession):
        for _ in range(3):
            await _make_entity_revision(db_session)
        svc = RevisionReviewService(db_session)
        result = await svc.list_drafts(page=2, page_size=2)
        assert len(result.items) == 1
        assert result.has_more is False


# ---------------------------------------------------------------------------
# confirm
# ---------------------------------------------------------------------------

class TestConfirm:
    async def test_sets_status_confirmed(self, db_session: AsyncSession):
        rev = await _make_entity_revision(db_session, status="draft")
        svc = RevisionReviewService(db_session)
        reviewer = await _make_reviewer(db_session)
        ok = await svc.confirm("entity", rev.id, reviewed_by_user_id=reviewer.id)
        assert ok is True

        result = await db_session.execute(
            select(EntityRevision).where(EntityRevision.id == rev.id)
        )
        updated = result.scalar_one()
        assert updated.status == "confirmed"
        assert updated.confirmed_by_user_id == reviewer.id
        assert updated.confirmed_at is not None

    async def test_returns_false_for_unknown_id(self, db_session: AsyncSession):
        svc = RevisionReviewService(db_session)
        ok = await svc.confirm("entity", uuid4(), reviewed_by_user_id=uuid4())
        assert ok is False

    async def test_returns_false_for_already_confirmed(self, db_session: AsyncSession):
        rev = await _make_entity_revision(db_session, status="confirmed")
        svc = RevisionReviewService(db_session)
        ok = await svc.confirm("entity", rev.id, reviewed_by_user_id=uuid4())
        assert ok is False

    async def test_confirm_relation_revision(self, db_session: AsyncSession):
        rev = await _make_relation_revision(db_session, status="draft")
        svc = RevisionReviewService(db_session)
        reviewer = await _make_reviewer(db_session)
        ok = await svc.confirm("relation", rev.id, reviewed_by_user_id=reviewer.id)
        assert ok is True

        result = await db_session.execute(
            select(RelationRevision).where(RelationRevision.id == rev.id)
        )
        updated = result.scalar_one()
        assert updated.status == "confirmed"
        assert updated.confirmed_by_user_id == reviewer.id
        assert updated.confirmed_at is not None

    async def test_confirm_source_revision(self, db_session: AsyncSession):
        rev = await _make_source_revision(db_session, status="draft")
        svc = RevisionReviewService(db_session)
        reviewer = await _make_reviewer(db_session)
        ok = await svc.confirm("source", rev.id, reviewed_by_user_id=reviewer.id)
        assert ok is True

        result = await db_session.execute(
            select(SourceRevision).where(SourceRevision.id == rev.id)
        )
        updated = result.scalar_one()
        assert updated.confirmed_by_user_id == reviewer.id
        assert updated.confirmed_at is not None

    async def test_invalid_kind_raises(self, db_session: AsyncSession):
        svc = RevisionReviewService(db_session)
        with pytest.raises(ValueError, match="Unknown revision_kind"):
            await svc.confirm("bogus", uuid4(), reviewed_by_user_id=uuid4())

    async def test_confirm_sets_previous_revision_is_current_false(self, db_session: AsyncSession):
        """Confirming a draft revision must set all sibling revisions to is_current=False."""
        entity = Entity(id=uuid4())
        db_session.add(entity)
        await db_session.flush()

        # First revision: previously confirmed and currently active
        old_rev = EntityRevision(
            entity_id=entity.id,
            slug=f"entity-v1-{uuid4().hex[:6]}",
            is_current=True,
            status="confirmed",
        )
        db_session.add(old_rev)
        await db_session.flush()

        # New draft revision for the same entity (a new version pending review)
        new_rev = EntityRevision(
            entity_id=entity.id,
            slug=f"entity-v2-{uuid4().hex[:6]}",
            created_with_llm="gpt-4",
            is_current=False,
            status="draft",
        )
        db_session.add(new_rev)
        await db_session.flush()

        svc = RevisionReviewService(db_session)
        reviewer = await _make_reviewer(db_session)
        ok = await svc.confirm("entity", new_rev.id, reviewed_by_user_id=reviewer.id)
        assert ok is True

        result = await db_session.execute(
            select(EntityRevision).where(EntityRevision.entity_id == entity.id)
        )
        all_revisions = result.scalars().all()

        current_revisions = [r for r in all_revisions if r.is_current]
        assert len(current_revisions) == 1, "exactly one revision must be current after confirm"
        assert current_revisions[0].id == new_rev.id

        old_after = next(r for r in all_revisions if r.id == old_rev.id)
        assert old_after.is_current is False


# ---------------------------------------------------------------------------
# discard
# ---------------------------------------------------------------------------

class TestDiscard:
    async def test_deletes_draft_revision(self, db_session: AsyncSession):
        rev = await _make_entity_revision(db_session, status="draft")
        svc = RevisionReviewService(db_session)
        ok = await svc.discard("entity", rev.id)
        assert ok is True

        result = await db_session.execute(
            select(EntityRevision).where(EntityRevision.id == rev.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_returns_false_for_unknown_id(self, db_session: AsyncSession):
        svc = RevisionReviewService(db_session)
        ok = await svc.discard("entity", uuid4())
        assert ok is False

    async def test_returns_false_for_confirmed_revision(self, db_session: AsyncSession):
        rev = await _make_entity_revision(db_session, status="confirmed")
        svc = RevisionReviewService(db_session)
        ok = await svc.discard("entity", rev.id)
        assert ok is False

    async def test_discard_relation_revision(self, db_session: AsyncSession):
        rev = await _make_relation_revision(db_session, status="draft")
        svc = RevisionReviewService(db_session)
        ok = await svc.discard("relation", rev.id)
        assert ok is True

    async def test_invalid_kind_raises(self, db_session: AsyncSession):
        svc = RevisionReviewService(db_session)
        with pytest.raises(ValueError, match="Unknown revision_kind"):
            await svc.discard("bogus", uuid4())


# ---------------------------------------------------------------------------
# get_draft_counts
# ---------------------------------------------------------------------------

class TestGetDraftCounts:
    async def test_all_zero_when_empty(self, db_session: AsyncSession):
        svc = RevisionReviewService(db_session)
        counts = await svc.get_draft_counts()
        assert counts == {"entity": 0, "relation": 0, "source": 0, "total": 0}

    async def test_counts_per_kind(self, db_session: AsyncSession):
        await _make_entity_revision(db_session)
        await _make_entity_revision(db_session)
        await _make_relation_revision(db_session)
        svc = RevisionReviewService(db_session)
        counts = await svc.get_draft_counts()
        assert counts["entity"] == 2
        assert counts["relation"] == 1
        assert counts["source"] == 0
        assert counts["total"] == 3

    async def test_confirmed_not_counted(self, db_session: AsyncSession):
        await _make_entity_revision(db_session, status="confirmed")
        await _make_entity_revision(db_session, status="draft")
        svc = RevisionReviewService(db_session)
        counts = await svc.get_draft_counts()
        assert counts["entity"] == 1

    async def test_total_is_sum_of_all_kinds(self, db_session: AsyncSession):
        await _make_entity_revision(db_session)
        await _make_relation_revision(db_session)
        await _make_source_revision(db_session)
        svc = RevisionReviewService(db_session)
        counts = await svc.get_draft_counts()
        assert counts["total"] == counts["entity"] + counts["relation"] + counts["source"]

    async def test_non_current_drafts_are_not_counted(self, db_session: AsyncSession):
        current_revision = await _make_entity_revision(db_session)
        stale_revision = await _make_entity_revision(db_session)
        stale_revision.is_current = False
        await db_session.flush()

        svc = RevisionReviewService(db_session)
        counts = await svc.get_draft_counts()
        assert counts["entity"] == 1
        assert counts["total"] == 1


# ---------------------------------------------------------------------------
# Status defaults (model-level)
# ---------------------------------------------------------------------------

class TestStatusDefaults:
    async def test_entity_revision_defaults_to_confirmed(self, db_session: AsyncSession):
        """Manually-created revisions default to 'confirmed' without specifying status."""
        entity = Entity(id=uuid4())
        db_session.add(entity)
        await db_session.flush()

        rev = EntityRevision(
            entity_id=entity.id,
            slug="manual-entity",
            is_current=True,
            # No status specified
        )
        db_session.add(rev)
        await db_session.flush()
        assert rev.status == "confirmed"

    async def test_relation_revision_defaults_to_confirmed(self, db_session: AsyncSession):
        source = Source()
        db_session.add(source)
        await db_session.flush()
        source_rev = SourceRevision(
            source_id=source.id, kind="study", title="S", url="http://x.com",
            is_current=True, status="confirmed",
        )
        db_session.add(source_rev)
        await db_session.flush()

        relation = Relation(source_id=source.id)
        db_session.add(relation)
        await db_session.flush()
        rev = RelationRevision(relation_id=relation.id, is_current=True)
        db_session.add(rev)
        await db_session.flush()
        assert rev.status == "confirmed"

    async def test_source_revision_defaults_to_confirmed(self, db_session: AsyncSession):
        source = Source()
        db_session.add(source)
        await db_session.flush()
        rev = SourceRevision(
            source_id=source.id,
            kind="study",
            title="Some Source",
            url="http://example.com",
            is_current=True,
            # No status specified
        )
        db_session.add(rev)
        await db_session.flush()
        assert rev.status == "confirmed"


# ---------------------------------------------------------------------------
# llm_review_status
# ---------------------------------------------------------------------------

class TestLlmReviewStatus:
    """llm_review_status tracks the LLM provenance review outcome independently
    of the revision visibility status ('draft'/'confirmed')."""

    async def test_human_authored_revision_has_null_llm_review_status(self, db_session: AsyncSession):
        """Human-authored revisions leave llm_review_status as NULL."""
        entity = Entity(id=uuid4())
        db_session.add(entity)
        await db_session.flush()

        rev = EntityRevision(
            entity_id=entity.id,
            slug="human-authored",
            is_current=True,
            status="confirmed",
        )
        db_session.add(rev)
        await db_session.flush()
        assert rev.llm_review_status is None

    async def test_llm_revision_starts_as_pending_review(self, db_session: AsyncSession):
        """LLM-created revisions should carry llm_review_status='pending_review'."""
        entity = Entity(id=uuid4())
        db_session.add(entity)
        await db_session.flush()

        rev = EntityRevision(
            entity_id=entity.id,
            slug=f"llm-entity-{uuid4().hex[:6]}",
            created_with_llm="gpt-4",
            is_current=True,
            status="draft",
            llm_review_status="pending_review",
        )
        db_session.add(rev)
        await db_session.flush()
        assert rev.llm_review_status == "pending_review"

    async def test_confirm_sets_llm_review_status_confirmed_for_llm_revision(self, db_session: AsyncSession):
        """confirm() must update llm_review_status to 'confirmed' for LLM revisions."""
        rev = await _make_entity_revision(db_session, status="draft")
        rev.llm_review_status = "pending_review"
        await db_session.flush()

        svc = RevisionReviewService(db_session)
        reviewer = await _make_reviewer(db_session)
        ok = await svc.confirm("entity", rev.id, reviewed_by_user_id=reviewer.id)
        assert ok is True

        result = await db_session.execute(
            select(EntityRevision).where(EntityRevision.id == rev.id)
        )
        updated = result.scalar_one()
        assert updated.status == "confirmed"
        assert updated.llm_review_status == "confirmed"

    async def test_confirm_does_not_set_llm_review_status_for_human_revision(self, db_session: AsyncSession):
        """confirm() must NOT set llm_review_status on human-authored revisions."""
        entity = Entity(id=uuid4())
        db_session.add(entity)
        await db_session.flush()

        rev = EntityRevision(
            entity_id=entity.id,
            slug=f"human-draft-{uuid4().hex[:6]}",
            is_current=True,
            status="draft",
        )
        db_session.add(rev)
        await db_session.flush()

        svc = RevisionReviewService(db_session)
        reviewer = await _make_reviewer(db_session)
        ok = await svc.confirm("entity", rev.id, reviewed_by_user_id=reviewer.id)
        assert ok is True

        result = await db_session.execute(
            select(EntityRevision).where(EntityRevision.id == rev.id)
        )
        updated = result.scalar_one()
        assert updated.llm_review_status is None

    async def test_list_drafts_exposes_llm_review_status(self, db_session: AsyncSession):
        """DraftRevisionRead returned by list_drafts must include llm_review_status."""
        entity = Entity(id=uuid4())
        db_session.add(entity)
        await db_session.flush()

        rev = EntityRevision(
            entity_id=entity.id,
            slug=f"pending-{uuid4().hex[:6]}",
            created_with_llm="gpt-4",
            is_current=True,
            status="draft",
            llm_review_status="pending_review",
        )
        db_session.add(rev)
        await db_session.flush()

        svc = RevisionReviewService(db_session)
        result = await svc.list_drafts()
        assert result.total == 1
        assert result.items[0].llm_review_status == "pending_review"

    async def test_auto_verified_status_persisted(self, db_session: AsyncSession):
        """auto_verified is a valid llm_review_status value stored on the revision."""
        entity = Entity(id=uuid4())
        db_session.add(entity)
        await db_session.flush()

        rev = EntityRevision(
            entity_id=entity.id,
            slug=f"auto-{uuid4().hex[:6]}",
            created_with_llm="gpt-4",
            is_current=True,
            status="draft",
            llm_review_status="auto_verified",
        )
        db_session.add(rev)
        await db_session.flush()
        assert rev.llm_review_status == "auto_verified"
