import pytest
from uuid import uuid4

from sqlalchemy import select

from app.models.entity_merge_record import EntityMergeRecord
from app.models.entity_revision import EntityRevision
from app.models.source_revision import SourceRevision
from app.services.entity_merge_service import EntityMergeService
from app.services.entity_service import EntityService
from app.services.relation_service import RelationService
from app.services.source_service import SourceService
from app.schemas.entity import EntityWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite as RoleWrite
from app.schemas.source import SourceWrite


@pytest.mark.asyncio
class TestSourceDocumentRevisionProvenance:
    async def test_add_document_to_source_creates_new_revision(self, db_session, test_user):
        service = SourceService(db_session)
        created = await service.create(
            SourceWrite(
                kind="study",
                title="Source With Document",
                url="https://example.com/source",
            )
        )

        original_revision_result = await db_session.execute(
            select(SourceRevision).where(SourceRevision.source_id == created.id)
        )
        original_revisions = original_revision_result.scalars().all()
        assert len(original_revisions) == 1
        original_revision = original_revisions[0]

        await service.add_document_to_source(
            source_id=created.id,
            document_text="Extracted document body",
            document_format="pdf",
            document_file_name="study.pdf",
            user_id=test_user.id,
        )

        revision_result = await db_session.execute(
            select(SourceRevision)
            .where(SourceRevision.source_id == created.id)
            .order_by(SourceRevision.created_at.asc())
        )
        revisions = revision_result.scalars().all()

        assert len(revisions) == 2
        assert revisions[0].id == original_revision.id
        assert revisions[0].is_current is False
        assert revisions[0].document_text is None

        new_revision = revisions[1]
        assert new_revision.is_current is True
        assert new_revision.document_text == "Extracted document body"
        assert new_revision.document_format == "pdf"
        assert new_revision.document_file_name == "study.pdf"
        assert new_revision.created_by_user_id == test_user.id


@pytest.mark.asyncio
class TestEntityMergeProvenance:
    async def test_merge_entities_records_merge_provenance(self, db_session, test_user):
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)
        merge_service = EntityMergeService(db_session)

        source_entity = await entity_service.create(
            EntityWrite(slug="source-entity", kind="concept")
        )
        target_entity = await entity_service.create(
            EntityWrite(slug="target-entity", kind="concept")
        )
        source = await source_service.create(
            SourceWrite(kind="study", title="Merge Study", url="https://example.com/merge")
        )

        await relation_service.create(
            RelationWrite(
                source_id=str(source.id),
                kind="effect",
                confidence=0.8,
                direction="supports",
                roles=[RoleWrite(role_type="subject", entity_id=str(source_entity.id))],
            )
        )

        result = await merge_service.merge_entities(
            source_entity.id,
            target_entity.id,
            merged_by_user_id=test_user.id,
        )

        merge_record_result = await db_session.execute(select(EntityMergeRecord))
        merge_records = merge_record_result.scalars().all()
        assert len(merge_records) == 1

        merge_record = merge_records[0]
        assert merge_record.source_entity_id == source_entity.id
        assert merge_record.target_entity_id == target_entity.id
        assert merge_record.merged_by_user_id == test_user.id
        assert merge_record.source_slug == "source-entity"
        assert merge_record.target_slug == "target-entity"

        source_revision_result = await db_session.execute(
            select(EntityRevision).where(EntityRevision.entity_id == source_entity.id)
        )
        source_revisions = source_revision_result.scalars().all()
        assert source_revisions
        assert all(revision.is_current is False for revision in source_revisions)

        assert result.merge_recorded is True
