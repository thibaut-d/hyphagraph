from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.llm.schemas import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractedRelationEvidenceContext,
    ExtractedRole,
)
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.staged_extraction import ExtractionStatus, ExtractionType, StagedExtraction
from app.models.ui_category import UiCategory
from app.schemas.entity import EntityPrefillDraft
from app.schemas.source import SourceWrite
from app.services.document_extraction_workflow import (
    ExtractedBatch,
    ReviewSummary,
    build_extraction_preview_with_service,
    build_link_suggestions,
    fetch_document_from_url,
    load_source_document_text,
    reconcile_staged_extractions,
    save_extraction_to_graph,
    stage_review_batch,
)
from app.services.pubmed_fetcher import PubMedArticle
from app.services.source_service import SourceService
from app.services.url_fetcher import UrlFetchResult
from app.utils.errors import ValidationException


def build_extracted_entity(slug: str) -> ExtractedEntity:
    return ExtractedEntity(
        slug=slug,
        summary=f"{slug} description",
        category="drug",
        confidence="high",
        text_span=f"{slug} mention",
    )


def build_extracted_relation(agent_slug: str, target_slug: str) -> ExtractedRelation:
    return ExtractedRelation(
        relation_type="treats",
        roles=[
            ExtractedRole(entity_slug=agent_slug, role_type="agent"),
            ExtractedRole(entity_slug=target_slug, role_type="target"),
        ],
        confidence="medium",
        text_span=f"{agent_slug} treats {target_slug}",
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
class TestFetchDocumentFromUrl:
    async def test_rejects_empty_generic_url_text(self, db_session):
        source_id = uuid4()

        class FakePubMedFetcher:
            def extract_pmid_from_url(self, url):
                return None

        class FakeUrlFetcher:
            async def fetch_url(self, url):
                return UrlFetchResult(
                    text="   ",
                    url=url,
                    title=None,
                    char_count=0,
                    truncated=False,
                    warnings=[],
                )

        with pytest.raises(ValidationException) as exc_info:
            await fetch_document_from_url(
                db_session,
                source_id=source_id,
                url="https://example.com/blank",
                pubmed_fetcher_factory=FakePubMedFetcher,
                url_fetcher_factory=FakeUrlFetcher,
            )

        assert exc_info.value.error_detail.message == "Fetched document has no extractable text"
        assert exc_info.value.error_detail.context == {
            "source_id": str(source_id),
            "url": "https://example.com/blank",
        }

    async def test_rejects_empty_pubmed_text(self, db_session):
        source_id = uuid4()

        class FakePubMedFetcher:
            def extract_pmid_from_url(self, url):
                return "41003152"

            async def fetch_by_pmid(self, pmid):
                return PubMedArticle(
                    pmid=pmid,
                    title="Management of Juvenile Fibromyalgia",
                    abstract="",
                    authors=[],
                    journal=None,
                    year=2025,
                    doi=None,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    full_text="",
                )

        with pytest.raises(ValidationException) as exc_info:
            await fetch_document_from_url(
                db_session,
                source_id=source_id,
                url="https://pubmed.ncbi.nlm.nih.gov/41003152/",
                pubmed_fetcher_factory=FakePubMedFetcher,
            )

        assert exc_info.value.error_detail.message == "Fetched document has no extractable text"
        assert exc_info.value.error_detail.context == {
            "source_id": str(source_id),
            "url": "https://pubmed.ncbi.nlm.nih.gov/41003152/",
        }


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
                entity_results=[SimpleNamespace()],
                relation_results=[SimpleNamespace()],
            ),
            review_service_factory=FakeReviewService,
        )

        assert summary == ReviewSummary(
            needs_review_count=1,
            auto_verified_count=2,
            avg_validation_score=pytest.approx(0.775),
        )

    async def test_stage_review_batch_only_passes_entities_and_relations(self, db_session):
        class FakeReviewService:
            stage_batch_kwargs = None

            def __init__(self, **kwargs):
                self.kwargs = kwargs

            async def stage_batch(self, **kwargs):
                FakeReviewService.stage_batch_kwargs = kwargs
                return []

        await stage_review_batch(
            db_session,
            source_id=uuid4(),
            extracted_batch=ExtractedBatch(
                entities=[build_extracted_entity("duloxetine")],
                relations=[build_extracted_relation("duloxetine", "fibromyalgia")],
                entity_results=[SimpleNamespace()],
                relation_results=[SimpleNamespace()],
            ),
            review_service_factory=FakeReviewService,
        )

        assert FakeReviewService.stage_batch_kwargs is not None
        assert set(FakeReviewService.stage_batch_kwargs) == {
            "entities",
            "relations",
            "source_id",
            "llm_model",
            "llm_provider",
            "auto_materialize",
            "commit",
        }

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
                    [SimpleNamespace()],
                    [SimpleNamespace()],
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

    async def test_build_extraction_preview_with_service_moves_contextual_pseudo_entities_into_scope_and_evidence_context(
        self,
        db_session,
    ):
        source_id = uuid4()
        entities = [
            build_extracted_entity("duloxetine"),
            ExtractedEntity(
                slug="fibromyalgia",
                summary="Fibromyalgia mention",
                category="disease",
                confidence="high",
                text_span="fibromyalgia",
            ),
            ExtractedEntity(
                slug="participants-1474",
                summary="Participant count mentioned in the source.",
                category="other",
                confidence="high",
                text_span="1474 participants",
            ),
            ExtractedEntity(
                slug="study-design-rct",
                summary="Randomized trial wording mentioned in the source.",
                category="other",
                confidence="high",
                text_span="randomized controlled trial",
            ),
            ExtractedEntity(
                slug="duration-12-weeks",
                summary="Duration wording mentioned in the source.",
                category="other",
                confidence="high",
                text_span="12 weeks",
            ),
        ]
        relations = [
            ExtractedRelation(
                relation_type="treats",
                roles=[
                    ExtractedRole(entity_slug="duloxetine", role_type="agent"),
                    ExtractedRole(entity_slug="fibromyalgia", role_type="target"),
                    ExtractedRole(entity_slug="participants-1474", role_type="sample_size"),
                    ExtractedRole(entity_slug="study-design-rct", role_type="study_design"),
                    ExtractedRole(entity_slug="duration-12-weeks", role_type="duration"),
                ],
                confidence="high",
                text_span="In a randomized controlled trial of 1474 participants, duloxetine improved fibromyalgia symptoms over 12 weeks.",
                evidence_context=ExtractedRelationEvidenceContext(
                    statement_kind="finding",
                    finding_polarity="supports",
                ),
            )
        ]

        class FakeExtractionService:
            def __init__(self, db):
                self.db = db

            async def extract_batch_with_validation_results(self, text):
                assert text == "source body"
                return (
                    entities,
                    relations,
                    [SimpleNamespace() for _ in entities],
                    [SimpleNamespace()],
                )

        class FakeReviewService:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            async def stage_batch(self, **kwargs):
                staged_relations = [relation for relation, _ in kwargs["relations"]]
                assert staged_relations[0].scope == {"duration": "12 weeks"}
                assert staged_relations[0].evidence_context is not None
                assert staged_relations[0].evidence_context.study_design == "randomized_controlled_trial"
                assert staged_relations[0].evidence_context.sample_size == 1474
                assert [role.entity_slug for role in staged_relations[0].roles] == ["duloxetine", "fibromyalgia"]
                staged_entities = [entity for entity, _ in kwargs["entities"]]
                assert [entity.slug for entity in staged_entities] == ["duloxetine", "fibromyalgia"]
                return [SimpleNamespace(status="pending", validation_score=0.7)]

        class FakeLinkingService:
            def __init__(self, db):
                self.db = db

            async def find_entity_matches(self, requested_entities):
                assert [entity.slug for entity in requested_entities] == ["duloxetine", "fibromyalgia"]
                return []

        preview = await build_extraction_preview_with_service(
            db_session,
            source_id=source_id,
            text="source body",
            extraction_service_factory=FakeExtractionService,
            review_service_factory=FakeReviewService,
            linking_service_factory=FakeLinkingService,
        )

        assert [entity.slug for entity in preview.entities] == ["duloxetine", "fibromyalgia"]
        assert preview.relations[0].scope == {"duration": "12 weeks"}
        assert preview.relations[0].evidence_context is not None
        assert preview.relations[0].evidence_context.sample_size == 1474
        assert preview.relations[0].evidence_context.study_design == "randomized_controlled_trial"
        assert [role.entity_slug for role in preview.relations[0].roles] == ["duloxetine", "fibromyalgia"]

    async def test_build_extraction_preview_with_service_infers_evidence_context_from_relation_text(
        self,
        db_session,
    ):
        source_id = uuid4()
        entities = [
            build_extracted_entity("fluoxetine"),
            ExtractedEntity(
                slug="fibromyalgia",
                summary="Fibromyalgia mention",
                category="disease",
                confidence="high",
                text_span="fibromyalgia",
            ),
            ExtractedEntity(
                slug="adults",
                summary="Adult population mention",
                category="population",
                confidence="high",
                text_span="adults",
            ),
            ExtractedEntity(
                slug="placebo",
                summary="Comparator mention",
                category="other",
                confidence="high",
                text_span="placebo",
            ),
        ]
        relations = [
            ExtractedRelation(
                relation_type="treats",
                roles=[
                    ExtractedRole(entity_slug="fluoxetine", role_type="agent"),
                    ExtractedRole(entity_slug="fibromyalgia", role_type="target"),
                    ExtractedRole(entity_slug="adults", role_type="population"),
                    ExtractedRole(entity_slug="placebo", role_type="control_group"),
                ],
                confidence="medium",
                text_span="two combined amitriptyline with fluoxetine (89 participants) in a randomized trial",
                notes="Combination therapy involving fluoxetine.",
                evidence_context=ExtractedRelationEvidenceContext(
                    statement_kind="finding",
                    evidence_strength="weak",
                ),
            )
        ]

        class FakeExtractionService:
            def __init__(self, db):
                self.db = db

            async def extract_batch_with_validation_results(self, text):
                assert text == "source body"
                return (
                    entities,
                    relations,
                    [SimpleNamespace() for _ in entities],
                    [SimpleNamespace()],
                )

        class FakeReviewService:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            async def stage_batch(self, **kwargs):
                staged_relations = [relation for relation, _ in kwargs["relations"]]
                assert staged_relations[0].evidence_context is not None
                assert staged_relations[0].evidence_context.sample_size == 89
                assert staged_relations[0].evidence_context.sample_size_text == "89 participants"
                assert staged_relations[0].evidence_context.study_design == "randomized_controlled_trial"
                return [SimpleNamespace(status="pending", validation_score=0.7)]

        class FakeLinkingService:
            def __init__(self, db):
                self.db = db

            async def find_entity_matches(self, requested_entities):
                return []

        preview = await build_extraction_preview_with_service(
            db_session,
            source_id=source_id,
            text="source body",
            extraction_service_factory=FakeExtractionService,
            review_service_factory=FakeReviewService,
            linking_service_factory=FakeLinkingService,
        )

        assert preview.relations[0].evidence_context is not None
        assert preview.relations[0].evidence_context.sample_size == 89
        assert preview.relations[0].evidence_context.sample_size_text == "89 participants"
        assert preview.relations[0].evidence_context.study_design == "randomized_controlled_trial"

    async def test_build_extraction_preview_with_service_revalidates_relations_after_context_normalization(
        self,
        db_session,
    ):
        source_id = uuid4()
        entities = [
            ExtractedEntity(
                slug="sample-size-41",
                summary="Sample size mention",
                category="other",
                confidence="high",
                text_span="41 participants",
            ),
            ExtractedEntity(
                slug="nausea",
                summary="Nausea mention",
                category="symptom",
                confidence="high",
                text_span="nausea",
            ),
            ExtractedEntity(
                slug="placebo",
                summary="Placebo mention",
                category="other",
                confidence="high",
                text_span="placebo",
            ),
        ]
        relations = [
            ExtractedRelation(
                relation_type="causes",
                roles=[
                    ExtractedRole(entity_slug="sample-size-41", role_type="agent"),
                    ExtractedRole(entity_slug="nausea", role_type="target"),
                    ExtractedRole(entity_slug="placebo", role_type="control_group"),
                ],
                confidence="medium",
                text_span="adverse events experienced by participants were not serious",
                notes="Common adverse event reported.",
            )
        ]

        class FakeExtractionService:
            def __init__(self, db):
                self.db = db

            async def extract_batch_with_validation_results(self, text):
                assert text == "adverse events experienced by participants were not serious"
                return (
                    entities,
                    relations,
                    [SimpleNamespace() for _ in entities],
                    [
                        SimpleNamespace(
                            is_valid=True,
                            confidence_adjustment=1.0,
                            validation_score=1.0,
                            flags=[],
                            matched_span="adverse events experienced by participants were not serious",
                        )
                    ],
                )

        class FakeReviewService:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            async def stage_batch(self, **kwargs):
                staged_relation, validation_result = kwargs["relations"][0]
                assert staged_relation.evidence_context is not None
                assert staged_relation.evidence_context.sample_size == 41
                assert validation_result.is_valid is False
                assert validation_result.validation_score == 0.0
                assert "invalid_contextual_core_role" in validation_result.flags
                assert "invalid_contextual_core_role:agent:sample-size-41" in validation_result.flags
                return [SimpleNamespace(status="pending", validation_score=validation_result.validation_score)]

        class FakeLinkingService:
            def __init__(self, db):
                self.db = db

            async def find_entity_matches(self, requested_entities):
                return []

        preview = await build_extraction_preview_with_service(
            db_session,
            source_id=source_id,
            text="adverse events experienced by participants were not serious",
            extraction_service_factory=FakeExtractionService,
            review_service_factory=FakeReviewService,
            linking_service_factory=FakeLinkingService,
        )

        assert preview.relations[0].roles == [
            ExtractedRole(entity_slug="sample-size-41", role_type="agent"),
            ExtractedRole(entity_slug="nausea", role_type="target"),
            ExtractedRole(entity_slug="placebo", role_type="control_group"),
        ]
        assert preview.avg_validation_score == 0.0


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
        prefill_draft = EntityPrefillDraft(
            slug="acetylsalicylic-acid",
            display_names={},
            summary={"en": "An analgesic drug."},
            aliases=[],
            ui_category_id=None,
        )

        class FakeBulkCreationService:
            def __init__(self, db):
                self.db = db

            async def bulk_create_entities(self, *, entities, entity_prefill_drafts, user_id):
                assert entity_prefill_drafts == {"aspirin": prefill_draft}
                return ({entities[0].slug: created_entity_id}, [])

            async def bulk_create_relations(self, *, relations, entity_mapping, source_id, user_id):
                assert source_id == source.id
                assert entity_mapping["aspirin"] == created_entity_id
                assert entity_mapping["pain"] == linked_entity_id
                assert relations[0].relation_type == "treats"
                return (relations, [created_relation_id], [])

        class FakeEntityPrefillService:
            def __init__(self, db):
                self.db = db

            async def generate_draft_for_extracted_entity(self, entity, user_language):
                assert entity.slug == "aspirin"
                assert user_language == "en"
                return prefill_draft

        request = SimpleNamespace(
            entities_to_create=[build_extracted_entity("aspirin")],
            entity_links={"pain": linked_entity_id},
            relations_to_create=[build_extracted_relation("aspirin", "pain")],
            user_language="en",
        )

        result = await save_extraction_to_graph(
            db_session,
            source_id=source.id,
            request=request,
            user_id=None,
            bulk_creation_service_factory=FakeBulkCreationService,
            entity_prefill_service_factory=FakeEntityPrefillService,
        )

        assert result.entities_created == 1
        assert result.entities_linked == 1
        assert result.relations_created == 1
        assert result.created_relation_ids == [created_relation_id]
        assert result.created_entity_ids == [created_entity_id]
        assert result.skipped_relations == []

    async def test_save_extraction_to_graph_persists_relation_evidence_context_and_direction(
        self, db_session, test_user
    ):
        source_service = SourceService(db_session)
        source = await source_service.create(
            SourceWrite(
                kind="study",
                title="Contextualized Extraction Source",
                url="https://example.com/contextualized-extraction",
            ),
            user_id=test_user.id,
        )

        aspirin = Entity()
        pain = Entity()
        db_session.add_all([aspirin, pain])
        await db_session.flush()
        db_session.add_all(
            [
                EntityRevision(entity_id=aspirin.id, slug="aspirin", is_current=True),
                EntityRevision(entity_id=pain.id, slug="pain", is_current=True),
            ]
        )
        await db_session.commit()

        request = SimpleNamespace(
            entities_to_create=[],
            entity_links={"aspirin": aspirin.id, "pain": pain.id},
            relations_to_create=[
                ExtractedRelation(
                    relation_type="treats",
                    roles=[
                        ExtractedRole(entity_slug="aspirin", role_type="agent"),
                        ExtractedRole(entity_slug="pain", role_type="target"),
                    ],
                    confidence="high",
                    text_span="In a randomized controlled trial (n=120), aspirin did not improve pain versus placebo.",
                    notes="Null effect in the randomized comparison.",
                    evidence_context=ExtractedRelationEvidenceContext(
                        statement_kind="finding",
                        finding_polarity="contradicts",
                        evidence_strength="strong",
                        study_design="randomized_controlled_trial",
                        sample_size=120,
                        sample_size_text="n=120",
                        assertion_text="Aspirin did not improve pain versus placebo.",
                        methodology_text="Randomized controlled trial.",
                        statistical_support="p=0.41",
                    ),
                )
            ],
            user_language="en",
        )

        result = await save_extraction_to_graph(
            db_session,
            source_id=source.id,
            request=request,
            user_id=test_user.id,
        )

        assert result.relations_created == 1

        revision_result = await db_session.execute(
            select(RelationRevision).where(
                RelationRevision.relation_id == result.created_relation_ids[0],
                RelationRevision.is_current.is_(True),
            )
        )
        revision = revision_result.scalar_one()
        assert revision.direction == "contradicts"
        assert revision.scope == {
            "evidence_context": {
                "statement_kind": "finding",
                "finding_polarity": "contradicts",
                "evidence_strength": "strong",
                "study_design": "randomized_controlled_trial",
                "sample_size": 120,
                "sample_size_text": "n=120",
                "assertion_text": "Aspirin did not improve pain versus placebo.",
                "methodology_text": "Randomized controlled trial.",
                "statistical_support": "p=0.41",
            }
        }

    async def test_save_extraction_to_graph_applies_prefill_to_new_entities(
        self, db_session, test_user
    ):
        source_service = SourceService(db_session)
        source = await source_service.create(
            SourceWrite(
                kind="study",
                title="Prefill Extraction Source",
                url="https://example.com/prefill-extraction",
            ),
            user_id=test_user.id,
        )
        category = UiCategory(slug="drug", labels={"en": "Drug"}, order=1)
        db_session.add(category)
        await db_session.flush()

        class FakeEntityPrefillService:
            def __init__(self, db):
                self.db = db

            async def generate_draft_for_extracted_entity(self, entity, user_language):
                assert entity.slug == "aspirin"
                assert user_language == "fr"
                return EntityPrefillDraft(
                    slug="acetylsalicylic-acid",
                    display_names={"en": "Acetylsalicylic acid", "fr": "Acide acétylsalicylique"},
                    summary={
                        "en": "A nonsteroidal anti-inflammatory drug.",
                        "fr": "Un anti-inflammatoire non stéroïdien.",
                    },
                    aliases=[
                        {"term": "Aspirin", "language": None, "term_kind": "brand"},
                        {"term": "ASA", "language": "en", "term_kind": "abbreviation"},
                    ],
                    ui_category_id=category.id,
                )

        request = SimpleNamespace(
            entities_to_create=[build_extracted_entity("aspirin")],
            entity_links={},
            relations_to_create=[],
            user_language="fr",
        )

        result = await save_extraction_to_graph(
            db_session,
            source_id=source.id,
            request=request,
            user_id=test_user.id,
            entity_prefill_service_factory=FakeEntityPrefillService,
        )

        assert result.entities_created == 1
        entity_id = result.created_entity_ids[0]

        revision_result = await db_session.execute(
            select(EntityRevision).where(
                EntityRevision.entity_id == entity_id,
                EntityRevision.is_current.is_(True),
            )
        )
        revision = revision_result.scalar_one()
        assert revision.slug == "acetylsalicylic-acid"
        assert revision.summary == {
            "en": "A nonsteroidal anti-inflammatory drug.",
            "fr": "Un anti-inflammatoire non stéroïdien.",
        }
        assert revision.ui_category_id == category.id
        assert revision.status == "confirmed"
        assert revision.llm_review_status == "confirmed"
        assert revision.confirmed_by_user_id == test_user.id
        assert revision.confirmed_at is not None

        terms_result = await db_session.execute(
            select(EntityTerm)
            .where(EntityTerm.entity_id == entity_id)
            .order_by(EntityTerm.display_order)
        )
        terms = terms_result.scalars().all()
        assert [(term.term, term.language, term.is_display_name, term.term_kind) for term in terms] == [
            ("Acetylsalicylic acid", "en", True, "alias"),
            ("Acide acétylsalicylique", "fr", True, "alias"),
            ("Aspirin", None, False, "brand"),
            ("ASA", "en", False, "abbreviation"),
        ]


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
        assert staged.reviewed_at.tzinfo is None

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

    async def test_rejects_previously_materialized_entity_when_linking_existing_slug(
        self, db_session, test_user
    ):
        source = await self._make_source(db_session)
        materialized_entity_id = await self._make_entity_id(db_session, "ibuprofen")

        staged = await self._make_staged(
            db_session,
            source_id=source.id,
            extraction_type=ExtractionType.ENTITY,
            extraction_data={"slug": "ibuprofen", "summary": "another drug", "category": "drug",
                             "confidence": "high", "text_span": "ibuprofen"},
            status=ExtractionStatus.AUTO_VERIFIED,
        )
        staged.materialized_entity_id = materialized_entity_id
        await db_session.flush()

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

        entity = await db_session.get(Entity, materialized_entity_id)
        assert entity is not None
        assert entity.is_rejected is True

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
                    {"entity_slug": "aspirin", "role_type": "agent"},
                    {"entity_slug": "pain", "role_type": "target"},
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

    async def test_returns_skipped_relation_details_on_parse_failure(self, db_session, test_user):
        """Corrupted staged relation data is skipped and returned as SkippedRelationDetail."""
        source = await self._make_source(db_session)

        staged = await self._make_staged(
            db_session,
            source_id=source.id,
            extraction_type=ExtractionType.RELATION,
            extraction_data={
                "relation_type": "treats",
                "roles": "not-a-list",
                "confidence": "high",
                "text_span": "aspirin treats pain",
                "notes": None,
            },
        )

        skipped_relations = await reconcile_staged_extractions(
            db_session,
            source_id=source.id,
            approved_entity_slugs_to_id={},
            rejected_entity_slugs=set(),
            approved_relations=[build_extracted_relation("aspirin", "pain")],
            approved_relation_ids=[uuid4()],
            user_id=test_user.id,
        )
        await db_session.commit()
        await db_session.refresh(staged)

        # Skipped list must contain the failing staged extraction
        assert staged.status == ExtractionStatus.PENDING
        assert staged.materialized_relation_id is None
        assert len(skipped_relations) == 1
        assert skipped_relations[0].extraction_id == staged.id
        assert skipped_relations[0].relation_type == "treats"
        assert skipped_relations[0].text_span == "aspirin treats pain"
        assert skipped_relations[0].error  # non-empty parse error message

    async def test_valid_relations_processed_alongside_corrupt_ones(self, db_session, test_user):
        """Valid staged relations are approved even when a sibling has corrupt data."""
        source = await self._make_source(db_session)
        relation_id = await self._make_relation_id(db_session, source.id)
        valid_rel = build_extracted_relation("aspirin", "pain")

        # One valid staged relation
        staged_good = await self._make_staged(
            db_session,
            source_id=source.id,
            extraction_type=ExtractionType.RELATION,
            extraction_data=valid_rel.model_dump(),
        )
        # One corrupted staged relation
        staged_bad = await self._make_staged(
            db_session,
            source_id=source.id,
            extraction_type=ExtractionType.RELATION,
            extraction_data={"bad": "payload"},
        )

        skipped_relations = await reconcile_staged_extractions(
            db_session,
            source_id=source.id,
            approved_entity_slugs_to_id={},
            rejected_entity_slugs=set(),
            approved_relations=[valid_rel],
            approved_relation_ids=[relation_id],
            user_id=test_user.id,
        )

        await db_session.commit()
        await db_session.refresh(staged_good)
        await db_session.refresh(staged_bad)

        assert staged_good.status == ExtractionStatus.APPROVED
        assert staged_good.materialized_relation_id == relation_id

        assert len(skipped_relations) == 1
        assert skipped_relations[0].extraction_id == staged_bad.id
        assert staged_bad.status == ExtractionStatus.PENDING
