from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.schemas.relation import (
    RelationWrite,
    RelationRead,
    RelationRevisionRead,
    RoleRevisionRead,
)


def relation_revision_from_write(payload: RelationWrite) -> dict:
    """
    Convert RelationWrite payload to RelationRevision data dict.

    Returns a dict (not ORM instance) for flexibility with revision helpers.
    Does NOT include roles - those are handled separately.
    """
    return {
        "kind": payload.kind,
        "direction": payload.direction,
        "confidence": payload.confidence,
        "scope": payload.scope,
        "notes": payload.notes,
        "created_with_llm": payload.created_with_llm,
    }


def relation_to_read(
    relation: Relation, current_revision: RelationRevision
) -> RelationRead:
    """
    ORM → Read

    Combines base relation + current revision data.
    """
    # Convert role revisions to read schema
    roles = [
        RoleRevisionRead(
            id=role.id,
            relation_revision_id=role.relation_revision_id,
            entity_id=role.entity_id,
            role_type=role.role_type,
            weight=role.weight,
            coverage=role.coverage,
        )
        for role in current_revision.roles
    ]

    return RelationRead(
        id=relation.id,
        created_at=relation.created_at,
        source_id=relation.source_id,
        kind=current_revision.kind,
        direction=current_revision.direction,
        confidence=current_revision.confidence,
        scope=current_revision.scope,
        notes=current_revision.notes,
        roles=roles,
    )


def relation_revision_to_read(revision: RelationRevision) -> RelationRevisionRead:
    """Convert RelationRevision ORM to RelationRevisionRead schema."""
    roles = [
        RoleRevisionRead(
            id=role.id,
            relation_revision_id=role.relation_revision_id,
            entity_id=role.entity_id,
            role_type=role.role_type,
            weight=role.weight,
            coverage=role.coverage,
        )
        for role in revision.roles
    ]

    return RelationRevisionRead(
        id=revision.id,
        relation_id=revision.relation_id,
        kind=revision.kind,
        direction=revision.direction,
        confidence=revision.confidence,
        scope=revision.scope,
        notes=revision.notes,
        created_with_llm=revision.created_with_llm,
        created_by_user_id=revision.created_by_user_id,
        created_at=revision.created_at,
        is_current=revision.is_current,
        roles=roles,
    )