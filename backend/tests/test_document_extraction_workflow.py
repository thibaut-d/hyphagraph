from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.llm.schemas import ExtractedEntity, ExtractedRelation, ExtractedRole
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.staged_extraction import ExtractionStatus, ExtractionType, StagedExtraction
from app.schemas.source import SourceWrite
from app.services.document_extraction_workflow import (
    ExtractedBatch,
    ReviewSummary,
    build_extraction_preview_with_service,
    build_link_suggestions,
    load_source_document_text,
    reconcile_staged_extractions,
    save_extraction_to_graph,
    stage_review_batch,
)
from app.services.source_service import SourceService
from app.utils.errors import ValidationException


def build_extracted_entity(slug: str) -> ExtractedEntity:
    return ExtractedEntity(
        slug=slug,
        summary=f"{slug} description",
        category="drug",
        confidence="high",
        text_span=f"{slug} mention",
    )


def build_extracted_relation(subject_slug: str, object_slug: str) -> ExtractedRelation:
    return ExtractedRelation(
        relation_type="treats",
        roles=[
            ExtractedRole(entity_slug=subject_slug, role_type="subject"),
            ExtractedRole(entity_slug=object_slug, role_type="object"),
        ],
        confidence="medium",
        text_span=f"{subject_slug} treats {object_slug}",
    )


@pytest.mark.asyncio
class TestLoadSourceDocumentText:
    async def test_returns_current_document_text(self, db_session, test_user):
        source_service = SourceService(db_session)
        source = await source_service.create(
            SourceWrite(
                kind="study",
                title="Workflow Source",
                url="https://example.com/workflow",
            ),
            user_id=test_user.id,
        )

        await source_service.add_document_to_source(
            source_id=source.id,
            document_text="document body",
            document_format="txt",
            document_file_name="workflow.txt",
            user_id=test_user.id,
        )

        result = await load_source_document_text(db_session, source.id)

        assert result == "document body"

    async def test_raises_when_document_missing(self, db_session):
        source_service = SourceService(db_session)
        source = await source_service.create(
            SourceWrite(
                kind="study",
                title="Missing Document",
                url="https://example.com/no-document",
            )
        )

        with pytest.raises(ValidationException) as exc_info:
            await load_source_document_text(db_session, source.id)

        assert exc_info.value.error_detail.message == "Source has no uploaded document"
        assert exc_info.value.error_detail.context == {"source_id": str(source.id)}


@pytest.mark.asyncio
class TestReviewAndLinkWorkflow:
    async def test_stage_review_batch_summarizes_review_outcomes(self, db_session):
        staged_items = [
            SimpleNamespace(status="pending", validation_score=0.6),
            SimpleNamespace(status="auto_verified", validation_score=0.95),
            SimpleNamespace(status="auto_verified", validation_score=None),
        ]

        class FakeReviewService:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            async def stage_batch(self, **kwargs):
                self.stage_batch_kwargs = kwargs
                return staged_items

        summary = await stage_review_batch(
            db_session,
            source_id=uuid4(),
            extracted_batch=ExtractedBatch(
                entities=[build_extracted_entity("aspirin")],
                relations=[build_extracted_relation("aspirin", "pain")],
                claims=[],
                entity_results=[SimpleNamespace()],
                relation_results=[SimpleNamespace()],
                claim_results=[],
            ),
            review_service_factory=FakeReviewService,
        )

        assert summary == ReviewSummary(
            needs_review_count=1,
            auto_verified_count=2,
            avg_validation_score=pytest.approx(0.775),
        )

    async def test_build_link_suggestions_maps_match_payloads(self, db_session):
        match = SimpleNamespace(
            extracted_slug="aspirin",
            matched_entity_id=uuid4(),
            matched_entity_slug="acetylsalicylic-acid",
            confidence=0.92,
            match_type="synonym",
        )

        class FakeLinkingService:
            def __init__(self, db):
                self.db = db

            async def find_entity_matches(self, entities):
                assert len(entities) == 1
                assert entities[0].slug == "aspirin"
                return [match]

        suggestions = await build_link_suggestions(
            db_session,
            entities=[build_extracted_entity("aspirin")],
            linking_service_factory=FakeLinkingService,
        )

        assert len(suggestions) == 1
        assert suggestions[0].extracted_slug == "aspirin"
        assert suggestions[0].matched_entity_id == match.matched_entity_id
        assert suggestions[0].matched_entity_slug == "acetylsalicylic-acid"
        assert suggestions[0].confidence == pytest.approx(0.92)
        assert suggestions[0].match_type == "synonym"

    async def test_build_extraction_preview_with_service_combines_extraction_review_and_links(
        self,
        db_session,
    ):
        source_id = uuid4()
        entities = [build_extracted_entity("aspirin")]
        relations = [build_extracted_relation("aspirin", "pain")]

        class FakeExtractionService:
            def __init__(self, db):
                self.db = db

            async def extract_batch_with_validation_results(self, text):
                assert text == "source body"
                return (
                    entities,
                    relations,
                    [],
                    [SimpleNamespace()],
                    [SimpleNamespace()],
                    [],
                )

        class FakeReviewService:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            async def stage_batch(self, **kwargs):
                assert kwargs["source_id"] == source_id
                return [
                    SimpleNamespace(status="pending", validation_score=0.7),
                    SimpleNamespace(status="auto_verified", validation_score=0.9),
                ]

        class FakeLinkingService:
            def __init__(self, db):
                self.db = db

            async def find_entity_matches(self, requested_entities):
                assert requested_entities == entities
                return [
                    SimpleNamespace(
                        extracted_slug="aspirin",
                        matched_entity_id=None,
                        matched_entity_slug=None,
                        confidence=0.2,
                        match_type="none",
                    )
                ]

        preview = await build_extraction_preview_with_service(
            db_session,
            source_id=source_id,
            text="source body",
            extraction_service_factory=FakeExtractionService,
            review_service_factory=FakeReviewService,
            linking_service_factory=FakeLinkingService,
        )

        assert preview.source_id == source_id
        assert preview.entities == entities
        assert preview.relations == relations
        assert preview.entity_count == 1
        assert preview.relation_count == 1
        assert preview.needs_review_count == 1
        assert preview.auto_verified_count == 1
        assert preview.avg_validation_score == pytest.approx(0.8)
        assert preview.link_suggestions[0].match_type == "none"


@pytest.mark.asyncio
class TestSaveExtractionToGraph:
    async def test_save_extraction_to_graph_uses_bulk_creation_service(self, db_session):
        source_service = SourceService(db_session)
        source = await source_service.create(
            SourceWrite(
                kind="study",
                title="Save Extraction Source",
                url="https://example.com/save-extraction",
            )
        )

        created_entity_id = uuid4()
        linked_entity_id = uuid4()
        created_relation_id = uuid4()

        class FakeBulkCreationService:
            def __init__(self, db):
                self.db = db

            async def bulk_create_entities(self, *, entities, user_id):
                return ({entities[0].slug: created_entity_id}, [])

            async def bulk_create_relations(self, *, relations, entity_mapping, source_id, user_id):
                assert source_id == source.id
                assert entity_mapping["aspirin"] == created_entity_id
                assert entity_mapping["pain"] == linked_entity_id
                assert relations[0].relation_type == "treats"
                return (relations, [created_relation_id], [])

        request = SimpleNamespace(
            entities_to_create=[build_extracted_entity("aspirin")],
            entity_links={"pain": linked_entity_id},
            relations_to_create=[build_extracted_relation("aspirin", "pain")],
        )

        result = await save_extraction_to_graph(
            db_session,
            source_id=source.id,
            request=request,
            user_id=None,
            bulk_creation_service_factory=FakeBulkCreationService,
        )

        assert result.entities_created == 1
        assert result.entities_linked == 1
        assert result.relations_created == 1
        assert result.created_relation_ids == [created_relation_id]
        assert set(result.created_entity_ids) == {created_entity_id, linked_entity_id}


@pytest.mark.asyncio
class TestReconcileStagedExtractions:
    """reconcile_staged_extractions links staged records to materialized graph items."""

    async def _make_source(self, db_session):
        source_service = SourceService(db_session)
        return await source_service.create(
            SourceWrite(kind="study", title="Reconcile Source", url="https://example.com/reconcile")
        )

    async def _make_entity_id(self, db_session, slug: str):
        entity = Entity()
        db_session.add(entity)
        await db_session.flush()
        db_session.add(EntityRevision(entity_id=entity.id, slug=slug, is_current=True))
        await db_session.flush()
        return entity.id

    async def _make_relation_id(self, db_session, source_id):
        relation = Relation(source_id=source_id)
        db_session.add(relation)
        await db_session.flush()
        db_session.add(RelationRevision(
            relation_id=relation.id, confidence=0.8, is_current=True
        ))
        await db_session.flush()
        return relation.id

    async def _make_staged(
        self,
        db_session,
        *,
        source_id,
        extraction_type: ExtractionType,
        extraction_data: dict,
        status: ExtractionStatus = ExtractionStatus.PENDING,
        validation_score: float = 0.8,
    ) -> StagedExtraction:
        staged = StagedExtraction(
            extraction_type=extraction_type,
            status=status,
            source_id=source_id,
            extraction_data=extraction_data,
            validation_score=validation_score,
            confidence_adjustment=1.0,
            validation_flags=[],
            auto_commit_eligible=False,
        )
        db_session.add(staged)
        await db_session.flush()
        await db_session.refresh(staged)
        return staged

    async def test_approves_entity_and_links_materialized_id(self, db_session, test_user):
        source = await self._make_source(db_session)
        entity_id = await self._make_entity_id(db_session, "aspirin")

        staged = await self._make_staged(
            db_session,
            source_id=source.id,
            extraction_type=ExtractionType.ENTITY,
            extraction_data={"slug": "aspirin", "summary": "a drug", "category": "drug",
                             "confidence": "high", "text_span": "aspirin"},
        )

        await reconcile_staged_extractions(
            db_session,
            source_id=source.id,
            approved_entity_slugs_to_id={"aspirin": entity_id},
            rejected_entity_slugs=set(),
            approved_relations=[],
            approved_relation_ids=[],
            user_id=test_user.id,
        )
        await db_session.commit()
        await db_session.refresh(staged)

        assert staged.status == ExtractionStatus.APPROVED
        assert staged.materialized_entity_id == entity_id
        assert staged.reviewed_by == test_user.id
        assert staged.reviewed_at is not None

    async def test_rejects_entity_link_slug(self, db_session, test_user):
        source = await self._make_source(db_session)

        staged = await self._make_staged(
            db_session,
            source_id=source.id,
            extraction_type=ExtractionType.ENTITY,
            extraction_data={"slug": "ibuprofen", "summary": "another drug", "category": "drug",
                             "confidence": "high", "text_span": "ibuprofen"},
        )

        await reconcile_staged_extractions(
            db_session,
            source_id=source.id,
            approved_entity_slugs_to_id={},
            rejected_entity_slugs={"ibuprofen"},
            approved_relations=[],
            approved_relation_ids=[],
            user_id=test_user.id,
        )
        await db_session.commit()
        await db_session.refresh(staged)

        assert staged.status == ExtractionStatus.REJECTED
        assert staged.materialized_entity_id is None
        assert staged.reviewed_by == test_user.id

    async def test_approves_relation_and_links_materialized_id(self, db_session, test_user):
        source = await self._make_source(db_session)
        relation_id = await self._make_relation_id(db_session, source.id)

        staged = await self._make_staged(
            db_session,
            source_id=source.id,
            extraction_type=ExtractionType.RELATION,
            extraction_data={
                "relation_type": "treats",
                "roles": [
                    {"entity_slug": "aspirin", "role_type": "subject"},
                    {"entity_slug": "pain", "role_type": "object"},
                ],
                "confidence": "high",
                "text_span": "aspirin treats pain",
                "notes": None,
            },
        )

        relation = build_extracted_relation("aspirin", "pain")
        await reconcile_staged_extractions(
            db_session,
            source_id=source.id,
            approved_entity_slugs_to_id={},
            rejected_entity_slugs=set(),
            approved_relations=[relation],
            approved_relation_ids=[relation_id],
            user_id=test_user.id,
        )
        await db_session.commit()
        await db_session.refresh(staged)

        assert staged.status == ExtractionStatus.APPROVED
        assert staged.materialized_relation_id == relation_id
        assert staged.reviewed_by == test_user.id

    async def test_claim_stays_pending(self, db_session, test_user):
        source = await self._make_source(db_session)
        aspirin_id = await self._make_entity_id(db_session, "aspirin-claim-test")

        staged = await self._make_staged(
            db_session,
            source_id=source.id,
            extraction_type=ExtractionType.CLAIM,
            extraction_data={
                "claim_type": "efficacy",
                "claim_text": "aspirin reduces fever",
                "entities_involved": ["aspirin-claim-test"],
                "evidence_strength": "moderate",
                "confidence": "medium",
                "text_span": "aspirin reduces fever",
            },
        )

        await reconcile_staged_extractions(
            db_session,
            source_id=source.id,
            approved_entity_slugs_to_id={"aspirin-claim-test": aspirin_id},
            rejected_entity_slugs=set(),
            approved_relations=[],
            approved_relation_ids=[],
            user_id=test_user.id,
        )
        await db_session.commit()
        await db_session.refresh(staged)

        assert staged.status == ExtractionStatus.PENDING

    async def test_no_staged_items_is_noop(self, db_session, test_user):
        source = await self._make_source(db_session)

        # Should not raise even with no staged extractions for this source
        await reconcile_staged_extractions(
            db_session,
            source_id=source.id,
            approved_entity_slugs_to_id={"aspirin": uuid4()},
            rejected_entity_slugs=set(),
            approved_relations=[build_extracted_relation("aspirin", "pain")],
            approved_relation_ids=[uuid4()],
            user_id=test_user.id,
        )
        # no assertion needed — just verify no exception raised

    async def test_unmatched_entity_stays_pending(self, db_session, test_user):
        """Staged entity not in the save request stays PENDING for review queue."""
        source = await self._make_source(db_session)

        staged = await self._make_staged(
            db_session,
            source_id=source.id,
            extraction_type=ExtractionType.ENTITY,
            extraction_data={"slug": "unselected-drug", "summary": "not chosen",
                             "category": "drug", "confidence": "low", "text_span": "drug"},
        )

        await reconcile_staged_extractions(
            db_session,
            source_id=source.id,
            approved_entity_slugs_to_id={"aspirin": uuid4()},
            rejected_entity_slugs=set(),
            approved_relations=[],
            approved_relation_ids=[],
            user_id=test_user.id,
        )
        await db_session.commit()
        await db_session.refresh(staged)

        assert staged.status == ExtractionStatus.PENDING
        assert staged.reviewed_by is None
