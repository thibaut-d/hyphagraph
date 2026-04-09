import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.llm.schemas import ExtractedClaim, ExtractedEntity, ExtractedRelation
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.staged_extraction import StagedExtraction
from app.utils.confidence import CONFIDENCE_FLOAT
from app.utils.relation_context import build_relation_context_payload
from app.utils.revision_helpers import create_new_revision

logger = logging.getLogger(__name__)


def _relation_scope(relation_data: ExtractedRelation) -> dict[str, object] | None:
    evidence_context = (
        relation_data.evidence_context.model_dump(exclude_none=True)
        if relation_data.evidence_context
        else None
    )
    return build_relation_context_payload(
        scope=relation_data.scope,
        evidence_context=evidence_context,
    )


def _relation_direction(relation_data: ExtractedRelation) -> str | None:
    if not relation_data.evidence_context:
        return None
    polarity = relation_data.evidence_context.finding_polarity
    if polarity in {"supports", "contradicts", "mixed", "neutral", "uncertain"}:
        return polarity
    return None


async def materialize_entity(
    db: AsyncSession,
    staged: StagedExtraction,
    user_id: UUID | None = None,
    llm_review_status: str = "pending_review",
) -> UUID:
    entity_data = ExtractedEntity(**staged.extraction_data)

    entity = Entity()
    db.add(entity)
    await db.flush()

    await create_new_revision(
        db=db,
        revision_class=EntityRevision,
        parent_id_field="entity_id",
        parent_id=entity.id,
        revision_data={
            "slug": entity_data.slug,
            "summary": {"en": entity_data.summary} if entity_data.summary else None,
            "status": "draft",
            "created_with_llm": staged.llm_model,
            "created_by_user_id": user_id,
            "llm_review_status": llm_review_status,
        },
        set_as_current=True,
    )

    logger.info("Materialized entity %s from staged extraction %s", entity.id, staged.id)
    return entity.id


async def materialize_relation(
    db: AsyncSession,
    staged: StagedExtraction,
    user_id: UUID | None = None,
    llm_review_status: str = "pending_review",
) -> UUID:
    relation_data = ExtractedRelation(**staged.extraction_data)

    relation = Relation(source_id=staged.source_id)
    db.add(relation)
    await db.flush()

    final_confidence = CONFIDENCE_FLOAT.get(relation_data.confidence, CONFIDENCE_FLOAT["medium"]) * staged.confidence_adjustment

    revision = await create_new_revision(
        db=db,
        revision_class=RelationRevision,
        parent_id_field="relation_id",
        parent_id=relation.id,
        revision_data={
            "kind": relation_data.relation_type,
            "direction": _relation_direction(relation_data),
            "confidence": final_confidence,
            "scope": _relation_scope(relation_data),
            "notes": {"en": relation_data.notes or relation_data.text_span}
            if relation_data.notes or relation_data.text_span
            else None,
            "status": "draft",
            "created_with_llm": staged.llm_model,
            "created_by_user_id": user_id,
            "llm_review_status": llm_review_status,
        },
        set_as_current=True,
    )

    for role_data in relation_data.roles:
        entity_result = await db.execute(
            select(EntityRevision)
            .where(EntityRevision.slug == role_data.entity_slug)
            .where(EntityRevision.is_current == True)  # noqa: E712
            .limit(1)
        )
        entity_revision = entity_result.scalar_one_or_none()

        if not entity_revision:
            raise ValueError(
                f"Entity with slug '{role_data.entity_slug}' not found; "
                f"cannot materialize relation {relation.id}"
            )

        db.add(
            RelationRoleRevision(
                relation_revision_id=revision.id,
                entity_id=entity_revision.entity_id,
                role_type=role_data.role_type,
            )
        )

    await db.flush()
    logger.info("Materialized relation %s from staged extraction %s", relation.id, staged.id)
    return relation.id


async def materialize_claim(
    db: AsyncSession,
    staged: StagedExtraction,
    user_id: UUID | None = None,
    llm_review_status: str = "pending_review",
) -> UUID:
    """Materialize a claim as a relation in the knowledge graph.

    Claims become relations where:
    - claim_type → relation kind
    - claim_text → notes (i18n)
    - evidence_strength → scope metadata
    - entities_involved → participant roles

    Raises ValueError if any entity slug in entities_involved cannot be resolved.
    """
    claim_data = ExtractedClaim(**staged.extraction_data)

    relation = Relation(source_id=staged.source_id)
    db.add(relation)
    await db.flush()

    final_confidence = CONFIDENCE_FLOAT.get(claim_data.confidence, CONFIDENCE_FLOAT["medium"]) * staged.confidence_adjustment

    revision = await create_new_revision(
        db=db,
        revision_class=RelationRevision,
        parent_id_field="relation_id",
        parent_id=relation.id,
        revision_data={
            "kind": claim_data.claim_type,
            "confidence": final_confidence,
            "notes": {"en": claim_data.claim_text},
            "scope": {"evidence_strength": claim_data.evidence_strength},
            "status": "draft",
            "created_with_llm": staged.llm_model,
            "created_by_user_id": user_id,
            "llm_review_status": llm_review_status,
        },
        set_as_current=True,
    )

    for slug in claim_data.entities_involved:
        entity_result = await db.execute(
            select(EntityRevision)
            .where(EntityRevision.slug == slug)
            .where(EntityRevision.is_current == True)  # noqa: E712
            .limit(1)
        )
        entity_revision = entity_result.scalar_one_or_none()

        if not entity_revision:
            raise ValueError(
                f"Entity with slug '{slug}' not found; "
                f"cannot materialize claim {relation.id}"
            )

        db.add(
            RelationRoleRevision(
                relation_revision_id=revision.id,
                entity_id=entity_revision.entity_id,
                role_type="participant",
            )
        )

    await db.flush()
    logger.info("Materialized claim %s as relation %s from staged extraction %s", claim_data.claim_type, relation.id, staged.id)
    return relation.id
