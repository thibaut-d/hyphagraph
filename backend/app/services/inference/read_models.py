from collections import defaultdict
from uuid import UUID, uuid4
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.mappers.relation_mapper import relation_to_read
from app.models.computed_relation import ComputedRelation
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.repositories.computed_relation_repo import ComputedRelationRepository
from app.repositories.relation_repo import RelationRepository
from app.schemas.inference import InferenceRead, RoleInference
from app.utils.hashing import compute_scope_hash

from .math import aggregate_evidence, compute_confidence, compute_disagreement


async def resolve_entity_slugs(
    db: AsyncSession,
    entity_ids: set[UUID],
) -> dict[UUID, str]:
    if not entity_ids:
        return {}

    result = await db.execute(
        select(EntityRevision.entity_id, EntityRevision.slug).where(
            EntityRevision.entity_id.in_(entity_ids),
            EntityRevision.is_current == True,
        )
    )
    return {row.entity_id: row.slug for row in result.all()}


def matches_scope(relation, scope_filter: dict) -> bool:
    if not relation.revisions:
        return False

    current_rev = next((revision for revision in relation.revisions if revision.is_current), None)
    if not current_rev:
        return False

    relation_scope = current_rev.scope
    if relation_scope is None:
        return False

    for key, value in scope_filter.items():
        if key not in relation_scope or relation_scope[key] != value:
            return False

    return True


async def build_grouped_inference_read(
    db: AsyncSession,
    entity_id: UUID,
    relations,
    role_inferences: list[RoleInference],
) -> InferenceRead:
    entity_ids: set[UUID] = set()
    for relation in relations:
        current_rev = next((revision for revision in relation.revisions if revision.is_current), None)
        if not current_rev or not current_rev.roles:
            continue

        for role in current_rev.roles:
            entity_ids.add(role.entity_id)

    entity_slug_map = await resolve_entity_slugs(db, entity_ids)

    grouped = defaultdict(list)
    for relation in relations:
        current_rev = next((revision for revision in relation.revisions if revision.is_current), None)
        relation_read = relation_to_read(
            relation,
            current_revision=current_rev,
            entity_slug_map=entity_slug_map,
        )
        kind = current_rev.kind if current_rev else relation.kind
        if kind:
            grouped[kind].append(relation_read)

    return InferenceRead(
        entity_id=entity_id,
        relations_by_kind=dict(grouped),
        role_inferences=role_inferences,
    )


def compute_role_inferences(relations, current_entity_id: UUID | None = None) -> list[RoleInference]:
    grouped_by_role = defaultdict(list)

    for relation in relations:
        if not relation.revisions:
            continue

        current_rev = next((revision for revision in relation.revisions if revision.is_current), None)
        if not current_rev or not current_rev.roles:
            continue

        for role in current_rev.roles:
            if current_entity_id and role.entity_id != current_entity_id:
                continue

            if current_rev.direction in {"positive", "supports"}:
                contribution = 1.0
            elif current_rev.direction in {"negative", "contradicts"}:
                contribution = -1.0
            else:
                contribution = role.weight if role.weight is not None else 1.0

            grouped_by_role[role.role_type].append(
                {
                    "weight": current_rev.confidence if current_rev.confidence is not None else 1.0,
                    "contribution": contribution,
                }
            )

    inferences: list[RoleInference] = []
    for role_type, relation_data_list in grouped_by_role.items():
        relations_data = [
            {"weight": item["weight"], "roles": {role_type: item["contribution"]}}
            for item in relation_data_list
        ]
        aggregated = aggregate_evidence(relations_data, role=role_type)
        coverage = float(len(relation_data_list))
        inferences.append(
            RoleInference(
                role_type=role_type,
                score=aggregated["score"],
                coverage=coverage,
                confidence=compute_confidence(coverage),
                disagreement=compute_disagreement(relations_data, role=role_type),
            )
        )

    return inferences


async def convert_cached_to_inference_read(
    *,
    db: AsyncSession,
    repo: RelationRepository,
    entity_id: UUID,
    cached_computed,
    scope_filter: Optional[dict],
) -> InferenceRead:
    role_inferences: list[RoleInference] = []

    if cached_computed.relation and cached_computed.relation.revisions:
        current_rev = next(
            (revision for revision in cached_computed.relation.revisions if revision.is_current),
            None,
        )
        if current_rev and current_rev.roles:
            for role_rev in current_rev.roles:
                coverage = role_rev.coverage or 0.0
                role_inferences.append(
                    RoleInference(
                        role_type=role_rev.role_type,
                        score=role_rev.weight,
                        coverage=coverage,
                        confidence=compute_confidence(coverage),
                        disagreement=cached_computed.uncertainty,
                    )
                )

    relations = await repo.list_by_entity(entity_id)
    if scope_filter:
        relations = [relation for relation in relations if matches_scope(relation, scope_filter)]

    return await build_grouped_inference_read(db, entity_id, relations, role_inferences)


async def cache_computed_inference(
    *,
    db: AsyncSession,
    computed_repo: ComputedRelationRepository,
    entity_id: UUID,
    scope_filter: Optional[dict],
    role_inferences: list[RoleInference],
) -> None:
    if not settings.SYSTEM_SOURCE_ID:
        return

    scope_hash = compute_scope_hash(entity_id, scope_filter)
    existing = await computed_repo.get_by_scope_hash(scope_hash, settings.INFERENCE_MODEL_VERSION)
    if existing:
        return

    relation = Relation(id=uuid4(), source_id=UUID(settings.SYSTEM_SOURCE_ID))
    db.add(relation)
    await db.flush()

    revision = RelationRevision(
        relation_id=relation.id,
        kind="computed_inference",
        direction="positive",
        confidence=1.0,
        scope=scope_filter,
        is_current=True,
    )
    db.add(revision)
    await db.flush()

    for role_inference in role_inferences:
        db.add(
            RelationRoleRevision(
                relation_revision_id=revision.id,
                entity_id=entity_id,
                role_type=role_inference.role_type,
                weight=role_inference.score,
                coverage=role_inference.coverage,
            )
        )

    await db.flush()

    avg_disagreement = (
        sum(role_inference.disagreement for role_inference in role_inferences) / len(role_inferences)
        if role_inferences
        else 0.0
    )
    db.add(
        ComputedRelation(
            relation_id=relation.id,
            scope_hash=scope_hash,
            model_version=settings.INFERENCE_MODEL_VERSION,
            uncertainty=avg_disagreement,
        )
    )
    await db.flush()
