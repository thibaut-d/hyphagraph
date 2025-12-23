from app.models.relation import Relation
from app.models.role import Role
from app.schemas.relation import RelationWrite, RelationRead
from app.schemas.role import RoleRead


def relation_from_write(payload: RelationWrite) -> Relation:
    """
    Write → ORM (Relation + Roles)
    """
    relation = Relation(
        source_id=payload.source_id,
        kind=payload.kind,
        direction=payload.direction,
        confidence=payload.confidence,
        notes=payload.notes,
    )

    relation.roles = [
        Role(
            entity_id=role.entity_id,
            role_type=role.role_type,
        )
        for role in payload.roles
    ]

    return relation


def relation_to_read(relation: Relation) -> RelationRead:
    """
    ORM → Read
    """
    return RelationRead(
        id=relation.id,
        source_id=relation.source_id,
        kind=relation.kind,
        direction=relation.direction,
        confidence=relation.confidence,
        notes=relation.notes,
        roles=[
            RoleRead(
                entity_id=role.entity_id,
                role_type=role.role_type,
            )
            for role in relation.roles
        ],
    )