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


def entity_to_read(entity: Entity, current_revision: EntityRevision) -> EntityRead:
    """
    ORM → Read

    Combines base entity + current revision data.
    """
    import json

    # Parse summary if it's a JSON string
    summary = current_revision.summary
    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except (json.JSONDecodeError, TypeError):
            summary = {"en": summary}  # Fallback to plain string

    return EntityRead(
        id=entity.id,
        created_at=entity.created_at,
        slug=current_revision.slug,
        summary=summary,
        ui_category_id=current_revision.ui_category_id,
        # Legacy fields (deprecated but still in schema for transition)
        kind=None,
        label=current_revision.slug,  # Use slug as label
        synonyms=[],
        ontology_ref=None,
    )


def entity_revision_to_read(revision: EntityRevision) -> EntityRevisionRead:
    """Convert EntityRevision ORM to EntityRevisionRead schema."""
    import json

    # Parse summary if it's a JSON string
    summary = revision.summary
    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except (json.JSONDecodeError, TypeError):
            summary = {"en": summary}

    return EntityRevisionRead(
        id=revision.id,
        entity_id=revision.entity_id,
        slug=revision.slug,
        summary=summary,
        ui_category_id=revision.ui_category_id,
        created_with_llm=revision.created_with_llm,
        created_by_user_id=revision.created_by_user_id,
        created_at=revision.created_at,
        is_current=revision.is_current,
    )