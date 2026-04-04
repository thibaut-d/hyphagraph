from sqlalchemy import and_

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision


def canonical_entity_predicate() -> object:
    """Entities that may participate in newly created canonical relations."""
    return and_(
        EntityRevision.is_current == True,  # noqa: E712
        EntityRevision.status == "confirmed",
        Entity.is_merged == False,  # noqa: E712
        Entity.is_rejected == False,  # noqa: E712
    )


def canonical_relation_predicate() -> object:
    """Current confirmed non-rejected relations visible in the canonical graph."""
    return and_(
        RelationRevision.is_current == True,  # noqa: E712
        RelationRevision.status == "confirmed",
        Relation.is_rejected == False,  # noqa: E712
    )
