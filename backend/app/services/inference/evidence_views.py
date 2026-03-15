from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.mappers.relation_mapper import relation_to_read
from app.models.relation import Relation
from app.schemas.relation import RelationRead

from .read_models import resolve_entity_slugs


@dataclass(frozen=True)
class RoleEvidenceRead:
    """Purpose-built relation view for explanation and detail consumers."""

    relation: RelationRead
    role_type: str
    role_weight: float
    contribution_weight: float
    contribution_direction: str


def _normalize_direction(direction: Optional[str]) -> str:
    if direction in {"positive", "supports"}:
        return "supports"
    if direction in {"negative", "contradicts"}:
        return "contradicts"
    return direction or "neutral"


def _build_role_evidence(relation: RelationRead, role_type: str) -> Optional[RoleEvidenceRead]:
    role = next((item for item in (relation.roles or []) if item.role_type == role_type), None)
    if role is None:
        return None

    relation_confidence = relation.confidence or 1.0
    relation_direction = _normalize_direction(relation.direction)

    if role.weight is not None:
        role_weight = role.weight
        contribution_weight = abs(role.weight) * relation_confidence
        contribution_direction = (
            "supports" if role.weight > 0 else "contradicts" if role.weight < 0 else relation_direction
        )
    else:
        if relation_direction == "supports":
            role_weight = relation_confidence
        elif relation_direction == "contradicts":
            role_weight = -relation_confidence
        else:
            role_weight = 0.0
        contribution_weight = relation_confidence
        contribution_direction = relation_direction

    return RoleEvidenceRead(
        relation=relation,
        role_type=role_type,
        role_weight=role_weight,
        contribution_weight=contribution_weight,
        contribution_direction=contribution_direction,
    )


async def build_role_evidence_views(
    db: AsyncSession,
    relations: list[Relation],
) -> dict[str, list[RoleEvidenceRead]]:
    entity_ids = set()
    for relation in relations:
        current_rev = next((revision for revision in relation.revisions if revision.is_current), None)
        if not current_rev or not current_rev.roles:
            continue

        for role in current_rev.roles:
            entity_ids.add(role.entity_id)

    entity_slug_map = await resolve_entity_slugs(db, entity_ids)

    role_views: dict[str, list[RoleEvidenceRead]] = {}
    for relation in relations:
        current_rev = next((revision for revision in relation.revisions if revision.is_current), None)
        if not current_rev:
            continue

        relation_read = relation_to_read(
            relation,
            current_revision=current_rev,
            entity_slug_map=entity_slug_map,
        )
        for role in relation_read.roles or []:
            role_view = _build_role_evidence(relation_read, role.role_type)
            if role_view is None:
                continue
            role_views.setdefault(role.role_type, []).append(role_view)

    return role_views
