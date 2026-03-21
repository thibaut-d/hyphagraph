from uuid import uuid4

import pytest

from app.schemas.relation import RelationRead, RoleRevisionRead
from app.schemas.source import SourceWrite
from app.services.entity_service import EntityService
from app.services.inference.evidence_views import _build_role_evidence, build_role_evidence_views
from app.services.relation_service import RelationService
from app.services.source_service import SourceService
from app.schemas.entity import EntityWrite
from app.schemas.relation import RelationWrite, RoleRevisionWrite


def build_relation_read(*, direction: str | None, confidence: float | None, weight: float | None) -> RelationRead:
    return RelationRead(
        id=uuid4(),
        created_at="2026-03-15T00:00:00Z",
        source_id=uuid4(),
        direction=direction,
        confidence=confidence,
        scope=None,
        notes=None,
        roles=[
            RoleRevisionRead(
                id=uuid4(),
                relation_revision_id=uuid4(),
                entity_id=uuid4(),
                role_type="subject",
                weight=weight,
                coverage=None,
                entity_slug="aspirin",
            )
        ],
    )


@pytest.mark.asyncio
class TestRoleEvidenceHelpers:
    async def test_build_role_evidence_uses_weight_sign_when_present(self):
        relation = build_relation_read(direction="supports", confidence=0.8, weight=-0.4)

        role_evidence = _build_role_evidence(relation, "subject")

        assert role_evidence is not None
        assert role_evidence.role_weight == pytest.approx(-0.4)
        assert role_evidence.contribution_weight == pytest.approx(0.32)
        assert role_evidence.contribution_direction == "contradicts"

    async def test_build_role_evidence_falls_back_to_direction_when_weight_missing(self):
        relation = build_relation_read(direction="negative", confidence=0.6, weight=None)

        role_evidence = _build_role_evidence(relation, "subject")

        assert role_evidence is not None
        assert role_evidence.role_weight == pytest.approx(-0.6)
        assert role_evidence.contribution_weight == pytest.approx(0.6)
        assert role_evidence.contribution_direction == "contradicts"

    async def test_build_role_evidence_views_groups_roles_and_resolves_entity_slugs(
        self,
        db_session,
    ):
        entity_service = EntityService(db_session)
        source_service = SourceService(db_session)
        relation_service = RelationService(db_session)

        subject = await entity_service.create(EntityWrite(slug="aspirin"))
        target = await entity_service.create(EntityWrite(slug="fibromyalgia"))
        source = await source_service.create(
            SourceWrite(
                kind="study",
                title="Evidence Source",
                url="https://example.com/evidence-source",
            )
        )

        relation_read = await relation_service.create(
            RelationWrite(
                source_id=source.id,
                kind="association",
                direction="supports",
                confidence=0.75,
                roles=[
                    RoleRevisionWrite(entity_id=subject.id, role_type="subject", weight=0.4),
                    RoleRevisionWrite(entity_id=target.id, role_type="object"),
                ],
            )
        )

        relations = await relation_service.repo.list_by_source(source.id)
        role_views = await build_role_evidence_views(db_session, relations)

        assert set(role_views) == {"subject", "object"}
        subject_view = role_views["subject"][0]
        object_view = role_views["object"][0]

        assert subject_view.relation.id == relation_read.id
        assert subject_view.relation.roles[0].entity_slug == "aspirin"
        assert object_view.relation.roles[1].entity_slug == "fibromyalgia"
        assert subject_view.contribution_direction == "supports"
        assert object_view.contribution_direction == "supports"
