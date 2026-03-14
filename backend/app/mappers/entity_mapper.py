import json

from typing import Any
from uuid import UUID
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.schemas.entity import EntityWrite, EntityRead, EntityRevisionRead


def entity_revision_from_write(payload: EntityWrite, entity_id: UUID | None = None) -> dict[str, Any]:
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
    # Parse summary if it's a JSON string
    summary = current_revision.summary
    if isinstance(summary, str):
        try:
            parsed = json.loads(summary)
            # Validate that parsed is a dictionary
            if isinstance(parsed, dict):
                summary = parsed
            else:
                # If not a dict, wrap it
                summary = {"en": str(parsed)}
        except (json.JSONDecodeError, TypeError, ValueError):
            # Fallback to plain string wrapped in dict
            summary = {"en": summary}
    elif isinstance(summary, dict):
        # Already a dict, use as-is
        summary = summary
    else:
        summary = None

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
    # Parse summary if it's a JSON string
    summary = revision.summary
    if isinstance(summary, str):
        try:
            parsed = json.loads(summary)
            # Validate that parsed is a dictionary
            if isinstance(parsed, dict):
                summary = parsed
            else:
                # If not a dict, wrap it
                summary = {"en": str(parsed)}
        except (json.JSONDecodeError, TypeError, ValueError):
            # Fallback to plain string wrapped in dict
            summary = {"en": summary}
    elif isinstance(summary, dict):
        # Already a dict, use as-is
        summary = summary
    else:
        summary = None

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
