from app.models.entity import Entity
from app.schemas.entity import EntityWrite, EntityRead


def entity_from_write(payload: EntityWrite) -> Entity:
    """
    Write → ORM
    """
    return Entity(
        kind=payload.kind,
        label=payload.label,
        synonyms=payload.synonyms,
        ontology_ref=payload.ontology_ref,
    )


def entity_to_read(entity: Entity) -> EntityRead:
    """
    ORM → Read
    """
    return EntityRead(
        id=entity.id,
        kind=entity.kind,
        label=entity.label,
        synonyms=entity.synonyms,
        ontology_ref=entity.ontology_ref,
    )