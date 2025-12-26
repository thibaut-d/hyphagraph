from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.schemas.entity import EntityWrite, EntityRead, EntityRevisionRead


def entity_revision_from_write(payload: EntityWrite, entity_id=None) -> dict:
    """
    Convert EntityWrite payload to EntityRevision data dict.

    Returns a dict (not ORM instance) for flexibility with revision helpers.
    """
    return {
        "slug": payload.slug,
        "summary": payload.summary,
        "ui_category_id": payload.ui_category_id,
        "created_with_llm": payload.created_with_llm,
    }


def entity_to_read(entity: Entity, current_revision: EntityRevision = None) -> EntityRead:
    """
    ORM → Read

    Combines base entity + current revision data.
    Falls back to deprecated fields if no revision exists.
    """
    if current_revision:
        return EntityRead(
            id=entity.id,
            created_at=entity.created_at,
            slug=current_revision.slug,
            summary=current_revision.summary,
            ui_category_id=current_revision.ui_category_id,
            # Legacy fields for backward compatibility
            kind=entity.kind,
            label=entity.label or current_revision.slug,  # Use slug as label fallback
            synonyms=entity.synonyms or [],
            ontology_ref=entity.ontology_ref,
        )
    else:
        # Fallback to legacy fields (for old data)
        return EntityRead(
            id=entity.id,
            created_at=entity.created_at,
            slug=entity.label or "",
            summary=None,
            ui_category_id=None,
            kind=entity.kind,
            label=entity.label,
            synonyms=entity.synonyms or [],
            ontology_ref=entity.ontology_ref,
        )


def entity_revision_to_read(revision: EntityRevision) -> EntityRevisionRead:
    """Convert EntityRevision ORM to EntityRevisionRead schema."""
    return EntityRevisionRead(
        id=revision.id,
        entity_id=revision.entity_id,
        slug=revision.slug,
        summary=revision.summary,
        ui_category_id=revision.ui_category_id,
        created_with_llm=revision.created_with_llm,
        created_by_user_id=revision.created_by_user_id,
        created_at=revision.created_at,
        is_current=revision.is_current,
    )