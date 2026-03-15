from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.llm.schemas import ExtractedEntity, ExtractedRelation, ExtractedRole
from app.schemas.source import SourceWrite
from app.services.document_extraction_workflow import (
    ExtractedBatch,
    ReviewSummary,
    build_extraction_preview_with_service,
    build_link_suggestions,
    load_source_document_text,
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

            async def bulk_create_entities(self, *, entities, source_id, user_id):
                assert source_id == source.id
                return {entities[0].slug: created_entity_id}

            async def bulk_create_relations(self, *, relations, entity_mapping, source_id, user_id):
                assert source_id == source.id
                assert entity_mapping["aspirin"] == created_entity_id
                assert entity_mapping["pain"] == linked_entity_id
                assert relations[0].relation_type == "treats"
                return [created_relation_id]

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
