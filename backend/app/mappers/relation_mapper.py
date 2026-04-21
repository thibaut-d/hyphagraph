from typing import TypedDict
from uuid import UUID
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision

from app.schemas.relation import (
    RelationWrite,
    RelationRead,
    RoleRevisionRead,
)
from app.utils.relation_context import (
    build_relation_context_payload,
    split_relation_context_payload,
)


class RelationRevisionPayload(TypedDict, total=False):
    kind: str | None
    direction: str | None
    confidence: float | None
    scope: dict[str, object] | None
    notes: dict[str, str] | None
    created_with_llm: str | None
    created_by_user_id: UUID | None


def relation_revision_from_write(payload: RelationWrite) -> RelationRevisionPayload:
    """
    Convert RelationWrite payload to RelationRevision data dict.

    Returns a dict (not ORM instance) for flexibility with revision helpers.
    Does NOT include roles - those are handled separately.
    """
    return {
        "kind": payload.kind,
        "direction": payload.direction,
        "confidence": payload.confidence,
        "scope": build_relation_context_payload(
            scope=payload.scope,
            evidence_context=payload.evidence_context,
        ),
        "notes": payload.notes,
        "created_with_llm": payload.created_with_llm,
    }


def relation_to_read(
    relation: Relation,
    current_revision: RelationRevision,
    entity_slug_map: dict[UUID, str] | None = None,
    *,
    source_title: str | None = None,
    source_year: int | None = None,
) -> RelationRead:
    """
    ORM → Read

    Combines base relation + current revision data.

    Args:
        relation: Base relation ORM object
        current_revision: Current revision ORM object
        entity_slug_map: Optional mapping of entity_id to slug for resolving entity names
    """
    # Convert role revisions to read schema
    scope, evidence_context = split_relation_context_payload(current_revision.scope)
    roles = [
        RoleRevisionRead(
            id=role.id,
            relation_revision_id=role.relation_revision_id,
            entity_id=role.entity_id,
            role_type=role.role_type,
            weight=role.weight,
            coverage=role.coverage,
            entity_slug=entity_slug_map.get(role.entity_id) if entity_slug_map else None,
            disagreement=getattr(role, "disagreement", None),
        )
        for role in current_revision.roles
    ]

    return RelationRead(
        id=relation.id,
        created_at=relation.created_at,
        updated_at=current_revision.created_at,
        source_id=relation.source_id,
        source_title=source_title,
        source_year=source_year,
        kind=current_revision.kind,
        direction=current_revision.direction,
        confidence=current_revision.confidence,
        scope=scope,
        evidence_context=evidence_context,
        notes=current_revision.notes,
        created_with_llm=current_revision.created_with_llm,
        status=current_revision.status,
        llm_review_status=current_revision.llm_review_status,
        roles=roles,
    )
