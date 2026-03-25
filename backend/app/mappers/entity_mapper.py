import json

from typing import TypedDict
from uuid import UUID
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.schemas.entity import EntityWrite, EntityRead


class EntityRevisionPayload(TypedDict, total=False):
    slug: str
    summary: dict[str, str] | None
    ui_category_id: UUID | None
    created_with_llm: str | None
    created_by_user_id: UUID | None


def _parse_summary(raw) -> dict[str, str] | None:
    """Normalise a summary value from the DB into an i18n dict or None."""
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
            return {"en": str(parsed)}
        except (json.JSONDecodeError, TypeError, ValueError):
            return {"en": raw}
    if isinstance(raw, dict):
        return raw
    return None


def entity_revision_from_write(payload: EntityWrite) -> EntityRevisionPayload:
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
    return EntityRead(
        id=entity.id,
        created_at=entity.created_at,
        updated_at=current_revision.created_at,
        slug=current_revision.slug,
        summary=_parse_summary(current_revision.summary),
        ui_category_id=current_revision.ui_category_id,
        created_with_llm=current_revision.created_with_llm,
        created_by_user_id=current_revision.created_by_user_id,
        status=current_revision.status,
        llm_review_status=current_revision.llm_review_status,
    )


