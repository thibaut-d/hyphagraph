import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.schemas import ExtractedClaim, ExtractedEntity, ExtractedRelation
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.staged_extraction import StagedExtraction

logger = logging.getLogger(__name__)


async def materialize_entity(db: AsyncSession, staged: StagedExtraction) -> UUID:
    entity_data = ExtractedEntity(**staged.extraction_data)

    entity = Entity()
    db.add(entity)
    await db.flush()

    db.add(
        EntityRevision(
            entity_id=entity.id,
            slug=entity_data.slug,
            summary={"en": entity_data.summary} if entity_data.summary else None,
            is_current=True,
            created_with_llm=staged.llm_model,
        )
    )
    await db.flush()

    logger.info("Materialized entity %s from staged extraction %s", entity.id, staged.id)
    return entity.id


async def materialize_relation(db: AsyncSession, staged: StagedExtraction) -> UUID:
    relation_data = ExtractedRelation(**staged.extraction_data)

    relation = Relation(source_id=staged.source_id)
    db.add(relation)
    await db.flush()

    confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
    final_confidence = confidence_map.get(relation_data.confidence, 0.7) * staged.confidence_adjustment

    revision = RelationRevision(
        relation_id=relation.id,
        kind=relation_data.relation_type,
        confidence=final_confidence,
        notes={"en": relation_data.text_span} if relation_data.text_span else None,
        is_current=True,
        created_with_llm=staged.llm_model,
    )
    db.add(revision)
    await db.flush()

    for role_data in relation_data.roles:
        entity_result = await db.execute(
            select(EntityRevision)
            .where(EntityRevision.slug == role_data.entity_slug)
            .where(EntityRevision.is_current == True)
            .limit(1)
        )
        entity_revision = entity_result.scalar_one_or_none()

        if not entity_revision:
            logger.warning(
                "Entity with slug '%s' not found, skipping role in relation %s",
                role_data.entity_slug,
                relation.id,
            )
            continue

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


async def materialize_claim(db: AsyncSession, staged: StagedExtraction) -> UUID:
    """Materialize a claim as a relation in the knowledge graph.

    Claims become relations where:
    - claim_type → relation kind
    - claim_text → notes (i18n)
    - evidence_strength → scope metadata
    - entities_involved → participant roles (skipped if entity not found)
    """
    claim_data = ExtractedClaim(**staged.extraction_data)

    relation = Relation(source_id=staged.source_id)
    db.add(relation)
    await db.flush()

    confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
    final_confidence = confidence_map.get(claim_data.confidence, 0.7) * staged.confidence_adjustment

    revision = RelationRevision(
        relation_id=relation.id,
        kind=claim_data.claim_type,
        confidence=final_confidence,
        notes={"en": claim_data.claim_text},
        scope={"evidence_strength": claim_data.evidence_strength},
        is_current=True,
        created_with_llm=staged.llm_model,
    )
    db.add(revision)
    await db.flush()

    for slug in claim_data.entities_involved:
        entity_result = await db.execute(
            select(EntityRevision)
            .where(EntityRevision.slug == slug)
            .where(EntityRevision.is_current == True)  # noqa: E712
            .limit(1)
        )
        entity_revision = entity_result.scalar_one_or_none()

        if not entity_revision:
            logger.warning(
                "Entity with slug '%s' not found, skipping participant in claim %s",
                slug,
                relation.id,
            )
            continue

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
