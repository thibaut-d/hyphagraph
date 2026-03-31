"""
Service for reviewing LLM-generated draft revisions.

Draft revisions (status='draft') are created by bulk_creation_service when
created_with_llm is set.  Humans confirm or discard them via this service.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.schemas.review import DraftRevisionRead, DraftRevisionListResponse

logger = logging.getLogger(__name__)


class RevisionReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    async def list_drafts(
        self,
        page: int = 1,
        page_size: int = 50,
        revision_kind: str | None = None,
    ) -> DraftRevisionListResponse:
        """Return paginated draft revisions across all revision tables."""
        rows: list[DraftRevisionRead] = []

        if revision_kind in (None, "entity"):
            rows.extend(await self._list_entity_drafts())
        if revision_kind in (None, "relation"):
            rows.extend(await self._list_relation_drafts())
        if revision_kind in (None, "source"):
            rows.extend(await self._list_source_drafts())

        # Sort newest first
        rows.sort(key=lambda r: r.created_at, reverse=True)

        total = len(rows)
        offset = (page - 1) * page_size
        page_items = rows[offset : offset + page_size]

        return DraftRevisionListResponse(
            items=page_items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total,
        )

    async def _list_entity_drafts(self) -> list[DraftRevisionRead]:
        result = await self.db.execute(
            select(EntityRevision).where(EntityRevision.status == "draft", EntityRevision.is_current == True)
        )
        return [
            DraftRevisionRead(
                id=r.id,
                revision_kind="entity",
                parent_id=r.entity_id,
                created_with_llm=r.created_with_llm,
                created_by_user_id=r.created_by_user_id,
                created_at=r.created_at,
                slug=r.slug,
                status=r.status,
                llm_review_status=r.llm_review_status,
            )
            for r in result.scalars().all()
        ]

    async def _list_relation_drafts(self) -> list[DraftRevisionRead]:
        result = await self.db.execute(
            select(RelationRevision).where(RelationRevision.status == "draft", RelationRevision.is_current == True)
        )
        return [
            DraftRevisionRead(
                id=r.id,
                revision_kind="relation",
                parent_id=r.relation_id,
                created_with_llm=r.created_with_llm,
                created_by_user_id=r.created_by_user_id,
                created_at=r.created_at,
                kind=r.kind,
                status=r.status,
                llm_review_status=r.llm_review_status,
            )
            for r in result.scalars().all()
        ]

    async def _list_source_drafts(self) -> list[DraftRevisionRead]:
        result = await self.db.execute(
            select(SourceRevision).where(SourceRevision.status == "draft", SourceRevision.is_current == True)
        )
        return [
            DraftRevisionRead(
                id=r.id,
                revision_kind="source",
                parent_id=r.source_id,
                created_with_llm=r.created_with_llm,
                created_by_user_id=r.created_by_user_id,
                created_at=r.created_at,
                kind=r.kind,
                title=r.title,
                status=r.status,
                llm_review_status=r.llm_review_status,
            )
            for r in result.scalars().all()
        ]

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------

    async def confirm(
        self, revision_kind: str, revision_id: UUID, reviewed_by_user_id: UUID
    ) -> bool:
        """Set status='confirmed' and is_current=True on a draft revision.  Returns False if not found."""
        model = self._model_for(revision_kind)
        # Use SELECT FOR UPDATE to prevent concurrent confirms (DF-DRV-C4)
        result = await self.db.execute(
            select(model).where(model.id == revision_id, model.status == "draft").with_for_update()
        )
        revision = result.scalar_one_or_none()
        if not revision:
            return False

        parent_id_field, _ = self._parent_for(revision_kind)
        parent_id = getattr(revision, parent_id_field)

        # Clear is_current on all other revisions for this parent (DF-DRV-C1)
        siblings_result = await self.db.execute(
            select(model).where(
                getattr(model, parent_id_field) == parent_id,
                model.id != revision_id,
            )
        )
        for sibling in siblings_result.scalars().all():
            sibling.is_current = False

        revision.status = "confirmed"
        revision.is_current = True
        revision.confirmed_by_user_id = reviewed_by_user_id
        revision.confirmed_at = datetime.now(timezone.utc)
        if revision.created_with_llm:
            revision.llm_review_status = "confirmed"
        await self.db.flush()
        await self.db.commit()
        logger.info(
            "Confirmed %s revision %s (llm=%s)",
            revision_kind,
            revision_id,
            revision.created_with_llm,
        )
        return True

    # ------------------------------------------------------------------
    # Discard
    # ------------------------------------------------------------------

    async def discard(
        self, revision_kind: str, revision_id: UUID
    ) -> bool:
        """Delete a draft revision.  Returns False if not found.

        If the discarded revision is the only revision for its parent object,
        the parent (Entity/Relation/Source) is also deleted so no orphan base
        row is left with zero revisions.
        """
        model = self._model_for(revision_kind)
        result = await self.db.execute(
            select(model).where(model.id == revision_id, model.status == "draft")
        )
        revision = result.scalar_one_or_none()
        if not revision:
            return False

        parent_id_field, parent_model = self._parent_for(revision_kind)
        parent_id = getattr(revision, parent_id_field)

        await self.db.delete(revision)
        await self.db.flush()

        # If there are no remaining revisions, delete the parent base row too.
        # Without this, the Entity/Relation/Source row is unreachable (queries
        # join through revisions) but wastes space and crashes if accessed by ID.
        sibling_count = await self.db.scalar(
            select(func.count()).where(getattr(model, parent_id_field) == parent_id)
        ) or 0
        if sibling_count == 0:
            parent = await self.db.get(parent_model, parent_id)
            if parent:
                await self.db.delete(parent)
                await self.db.flush()

        await self.db.commit()
        logger.info(
            "Discarded %s revision %s (llm=%s)",
            revision_kind,
            revision_id,
            revision.created_with_llm,
        )
        return True

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_draft_counts(self) -> dict[str, int]:
        """Return count of draft revisions per kind."""
        entity_count = await self.db.scalar(
            select(func.count()).where(EntityRevision.status == "draft", EntityRevision.is_current == True)
        ) or 0
        relation_count = await self.db.scalar(
            select(func.count()).where(RelationRevision.status == "draft", RelationRevision.is_current == True)
        ) or 0
        source_count = await self.db.scalar(
            select(func.count()).where(SourceRevision.status == "draft", SourceRevision.is_current == True)
        ) or 0
        return {
            "entity": entity_count,
            "relation": relation_count,
            "source": source_count,
            "total": entity_count + relation_count + source_count,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _model_for(revision_kind: str):
        mapping = {
            "entity": EntityRevision,
            "relation": RelationRevision,
            "source": SourceRevision,
        }
        model = mapping.get(revision_kind)
        if not model:
            raise ValueError(f"Unknown revision_kind: {revision_kind!r}")
        return model

    @staticmethod
    def _parent_for(revision_kind: str) -> tuple[str, type]:
        """Return (parent_id_field_name, parent_model_class) for a revision kind."""
        mapping = {
            "entity": ("entity_id", Entity),
            "relation": ("relation_id", Relation),
            "source": ("source_id", Source),
        }
        result = mapping.get(revision_kind)
        if not result:
            raise ValueError(f"Unknown revision_kind: {revision_kind!r}")
        return result
