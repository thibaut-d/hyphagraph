import pytest
from fastapi import status
from sqlalchemy import select

from app.llm.base import LLMError, LLMResponse
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.schemas.graph_cleaning import (
    DuplicateRelationApplyRequest,
    GraphCleaningCritiqueRequest,
    GraphCleaningDecisionWrite,
    RoleCorrectionItem,
    RoleCorrectionRequest,
)
from app.schemas.entity import EntityWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite
from app.schemas.source import SourceWrite
from app.services.entity_service import EntityService
from app.services.graph_cleaning_service import GraphCleaningService
from app.services.relation_service import RelationService
from app.services.source_service import SourceService


class FakeCritiqueLLM:
    def __init__(self):
        self.last_kwargs = None

    async def generate_json(self, **kwargs):
        self.last_kwargs = kwargs
        return {
            "items": [
                {
                    "candidate_fingerprint": "candidate-1",
                    "recommendation": "needs_human_review",
                    "rationale": "Similar labels but source context must be checked.",
                    "risks": ["false positive"],
                    "evidence_gaps": ["source span"],
                }
            ]
        }

    def get_model_name(self):
        return "fake-cleaning-model"

    async def generate(self, **kwargs):
        return LLMResponse(content="", model="fake-cleaning-model", usage={})

    def is_available(self):
        return True


class FailingCritiqueLLM(FakeCritiqueLLM):
    async def generate_json(self, **kwargs):
        self.last_kwargs = kwargs
        raise LLMError("LLM response was truncated before JSON was complete", finish_reason="length")


class StringListCritiqueLLM(FakeCritiqueLLM):
    async def generate_json(self, **kwargs):
        self.last_kwargs = kwargs
        return {
            "items": [
                {
                    "candidate_fingerprint": "candidate-1",
                    "recommendation": "reject",
                    "rationale": "Candidate is too broad.",
                    "risks": "Would collapse distinct evidence.",
                    "evidence_gaps": "Need source context.",
                }
            ]
        }


@pytest.mark.asyncio
async def test_duplicate_relation_analysis_groups_same_source_signature(db_session):
    entity_service = EntityService(db_session)
    source_service = SourceService(db_session)
    relation_service = RelationService(db_session)
    cleaning_service = GraphCleaningService(db_session)

    drug = await entity_service.create(EntityWrite(slug="duloxetine"))
    condition = await entity_service.create(EntityWrite(slug="fibromyalgia"))
    source = await source_service.create(
        SourceWrite(kind="study", title="Duplicate relation study", url="https://example.com/dup")
    )

    payload = RelationWrite(
        source_id=source.id,
        kind="treats",
        direction="supports",
        confidence=0.8,
        roles=[
            RoleRevisionWrite(entity_id=drug.id, role_type="agent"),
            RoleRevisionWrite(entity_id=condition.id, role_type="target"),
        ],
    )
    first = await relation_service.create(payload)
    second = await relation_service.create(payload)

    candidates = await cleaning_service.list_duplicate_relation_candidates()

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.relation_count == 2
    assert {item.relation_id for item in candidate.relations} == {first.id, second.id}
    assert candidate.source_title == "Duplicate relation study"
    assert {role.entity_slug for role in candidate.relations[0].roles} == {
        "duloxetine",
        "fibromyalgia",
    }


@pytest.mark.asyncio
async def test_role_consistency_analysis_flags_multiple_roles_for_same_kind(db_session):
    entity_service = EntityService(db_session)
    source_service = SourceService(db_session)
    relation_service = RelationService(db_session)
    cleaning_service = GraphCleaningService(db_session)

    shared = await entity_service.create(EntityWrite(slug="fibromyalgia"))
    duloxetine = await entity_service.create(EntityWrite(slug="duloxetine"))
    pain = await entity_service.create(EntityWrite(slug="pain"))
    source = await source_service.create(
        SourceWrite(kind="study", title="Role consistency study", url="https://example.com/roles")
    )

    await relation_service.create(
        RelationWrite(
            source_id=source.id,
            kind="associated_with",
            roles=[
                RoleRevisionWrite(entity_id=shared.id, role_type="condition"),
                RoleRevisionWrite(entity_id=pain.id, role_type="target"),
            ],
        )
    )
    await relation_service.create(
        RelationWrite(
            source_id=source.id,
            kind="associated_with",
            roles=[
                RoleRevisionWrite(entity_id=duloxetine.id, role_type="agent"),
                RoleRevisionWrite(entity_id=shared.id, role_type="target"),
            ],
        )
    )

    candidates = await cleaning_service.list_role_consistency_candidates()

    candidate = next(item for item in candidates if item.entity_slug == "fibromyalgia")
    assert candidate.relation_kind == "associated_with"
    assert {usage.role_type for usage in candidate.usages} == {"condition", "target"}


@pytest.mark.asyncio
async def test_decision_upsert_persists_review_status(db_session, test_user):
    service = GraphCleaningService(db_session)

    first = await service.upsert_decision(
        GraphCleaningDecisionWrite(
            candidate_type="entity_merge",
            candidate_fingerprint="entity-a-entity-b",
            status="needs_review",
            notes="Need source context.",
        ),
        test_user.id,
    )
    second = await service.upsert_decision(
        GraphCleaningDecisionWrite(
            candidate_type="entity_merge",
            candidate_fingerprint="entity-a-entity-b",
            status="dismissed",
            notes="Not the same entity.",
        ),
        test_user.id,
    )

    assert second.id == first.id
    assert second.status == "dismissed"
    assert len(await service.list_decisions()) == 1


@pytest.mark.asyncio
async def test_critique_candidates_returns_advisory_items(db_session):
    service = GraphCleaningService(db_session)
    llm = FakeCritiqueLLM()

    response = await service.critique_candidates(
        GraphCleaningCritiqueRequest(
            candidates=[
                {
                    "candidate_fingerprint": "candidate-1",
                    "candidate_type": "duplicate_relation",
                    "relations": [
                        {
                            "relation_id": "relation-1",
                            "roles": [
                                {
                                    "entity_slug": "duloxetine",
                                    "role_type": "agent",
                                    "extra": "not sent to the LLM",
                                }
                            ],
                        }
                    ],
                }
            ]
        ),
        llm,
    )

    assert response.model == "fake-cleaning-model"
    assert response.items[0].recommendation == "needs_human_review"
    assert response.items[0].risks == ["false positive"]
    assert llm.last_kwargs["max_tokens"] == 4000
    prompt = llm.last_kwargs["prompt"]
    assert "not sent to the LLM" not in prompt
    assert "duloxetine" in prompt


@pytest.mark.asyncio
async def test_critique_candidates_maps_llm_truncation_to_structured_error(db_session):
    service = GraphCleaningService(db_session)

    with pytest.raises(Exception) as exc_info:
        await service.critique_candidates(
            GraphCleaningCritiqueRequest(candidates=[{"candidate_fingerprint": "candidate-1"}]),
            FailingCritiqueLLM(),
        )

    assert exc_info.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc_info.value.error_detail.code == "LLM_API_ERROR"
    assert exc_info.value.error_detail.context == {"finish_reason": "length"}


@pytest.mark.asyncio
async def test_critique_candidates_accepts_string_risks_from_llm(db_session):
    service = GraphCleaningService(db_session)

    response = await service.critique_candidates(
        GraphCleaningCritiqueRequest(candidates=[{"candidate_fingerprint": "candidate-1"}]),
        StringListCritiqueLLM(),
    )

    assert response.items[0].risks == ["Would collapse distinct evidence."]
    assert response.items[0].evidence_gaps == ["Need source context."]


@pytest.mark.asyncio
async def test_apply_duplicate_relation_review_marks_relations_rejected(db_session, test_user):
    entity_service = EntityService(db_session)
    source_service = SourceService(db_session)
    relation_service = RelationService(db_session)
    cleaning_service = GraphCleaningService(db_session)

    drug = await entity_service.create(EntityWrite(slug="pregabalin"))
    condition = await entity_service.create(EntityWrite(slug="fibromyalgia"))
    source = await source_service.create(
        SourceWrite(kind="study", title="Duplicate apply study", url="https://example.com/apply")
    )
    relation = await relation_service.create(
        RelationWrite(
            source_id=source.id,
            kind="treats",
            roles=[
                RoleRevisionWrite(entity_id=drug.id, role_type="agent"),
                RoleRevisionWrite(entity_id=condition.id, role_type="target"),
            ],
        )
    )

    result = await cleaning_service.apply_duplicate_relation_review(
        DuplicateRelationApplyRequest(
            duplicate_relation_ids=[relation.id],
            rationale="Duplicate extraction from same source sentence.",
            candidate_fingerprint="dup-1",
        ),
        test_user.id,
    )

    assert result.status == "applied"
    stored = (await db_session.execute(select(Relation).where(Relation.id == relation.id))).scalar_one()
    assert stored.is_rejected is True


@pytest.mark.asyncio
async def test_apply_role_correction_creates_new_relation_revision(db_session, test_user):
    entity_service = EntityService(db_session)
    source_service = SourceService(db_session)
    relation_service = RelationService(db_session)
    cleaning_service = GraphCleaningService(db_session)

    entity = await entity_service.create(EntityWrite(slug="fibromyalgia"))
    outcome = await entity_service.create(EntityWrite(slug="pain"))
    source = await source_service.create(
        SourceWrite(kind="study", title="Role correction study", url="https://example.com/correct")
    )
    relation = await relation_service.create(
        RelationWrite(
            source_id=source.id,
            kind="associated_with",
            roles=[
                RoleRevisionWrite(entity_id=entity.id, role_type="condition"),
                RoleRevisionWrite(entity_id=outcome.id, role_type="target"),
            ],
        )
    )
    before_revisions = (
        await db_session.execute(
            select(RelationRevision).where(RelationRevision.relation_id == relation.id)
        )
    ).scalars().all()

    result = await cleaning_service.apply_role_correction(
        relation.id,
        RoleCorrectionRequest(
            corrections=[
                RoleCorrectionItem(
                    entity_id=entity.id,
                    from_role_type="condition",
                    to_role_type="target",
                )
            ],
            rationale="Entity is the asserted target in this relation.",
            candidate_fingerprint="role-1",
        ),
        test_user.id,
    )

    after_revisions = (
        await db_session.execute(
            select(RelationRevision).where(RelationRevision.relation_id == relation.id)
        )
    ).scalars().all()
    assert result.status == "applied"
    assert len(after_revisions) == len(before_revisions) + 1
