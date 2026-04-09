"""
Bulk creation service for atomically creating multiple entities and relations.

Handles batch creation from LLM extraction results, with transaction safety
and error handling for duplicate entities.
"""
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.llm.schemas import ExtractedEntity, ExtractedRelation
from app.schemas.common_types import SlugEntityMap
from app.schemas.entity import EntityPrefillDraft
from app.utils.revision_helpers import create_new_revision
from app.utils.confidence import CONFIDENCE_FLOAT
from app.utils.relation_context import build_relation_context_payload
from app.config import settings

logger = logging.getLogger(__name__)


def _build_relation_scope(extracted: ExtractedRelation) -> dict[str, object] | None:
    evidence_context = (
        extracted.evidence_context.model_dump(exclude_none=True)
        if extracted.evidence_context
        else None
    )
    return build_relation_context_payload(
        scope=extracted.scope,
        evidence_context=evidence_context,
    )


def _build_relation_direction(extracted: ExtractedRelation) -> str | None:
    if not extracted.evidence_context:
        return None
    polarity = extracted.evidence_context.finding_polarity
    if polarity in {"supports", "contradicts", "mixed", "neutral", "uncertain"}:
        return polarity
    return None


class BulkCreationService:
    """
    Service for bulk creation of entities and relations from LLM extraction.

    Provides atomic batch operations with single transaction commit.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize bulk creation service.

        Args:
            db: Database session for atomic transactions
        """
        self.db = db

    async def bulk_create_entities(
        self,
        entities: list[ExtractedEntity],
        entity_prefill_drafts: dict[str, EntityPrefillDraft] | None = None,
        user_id: UUID | None = None
    ) -> tuple[SlugEntityMap, list[str]]:
        """
        Bulk create entities with their first revisions.

        Creates both base Entity and EntityRevision for each entity in a
        single transaction. Handles duplicate slug errors by skipping and logging.

        Args:
            entities: List of extracted entities to create
            user_id: User creating the entities (for provenance)

        Returns:
            Tuple of (slug→entity_id mapping for created entities, list of warning strings
            describing any skipped entities)

        Raises:
            Exception: On database errors other than duplicate slugs
        """
        entity_mapping: SlugEntityMap = {}
        warnings = []
        prefill_drafts = entity_prefill_drafts or {}

        # Process entities one at a time using savepoints (begin_nested) so a duplicate-slug error
        # only rolls back that single entity, leaving all others intact.
        for extracted in entities:
            draft = prefill_drafts.get(extracted.slug)
            slug = draft.slug if draft else extracted.slug
            summary = draft.summary if draft else (
                {"en": extracted.summary} if extracted.summary else None
            )
            ui_category_id = draft.ui_category_id if draft else None
            try:
                async with self.db.begin_nested():
                    # Create base entity
                    entity = Entity()
                    self.db.add(entity)
                    await self.db.flush()  # Get entity.id

                    # Prepare revision data
                    revision_data = {
                        "slug": slug,
                        "summary": summary,
                        "ui_category_id": ui_category_id,
                        "created_with_llm": settings.OPENAI_MODEL,  # Track LLM provenance
                        "created_by_user_id": user_id,
                        # LLM-created revisions start as drafts pending human review
                        "status": "draft",
                        "llm_review_status": "pending_review",
                    }

                    # Create first revision
                    await create_new_revision(
                        db=self.db,
                        revision_class=EntityRevision,
                        parent_id_field='entity_id',
                        parent_id=entity.id,
                        revision_data=revision_data,
                        set_as_current=True,
                    )

                    # Map slug to entity_id (only reached if savepoint succeeds)
                    entity_mapping[extracted.slug] = entity.id

            except IntegrityError as e:
                # Savepoint was already rolled back; outer transaction is intact.
                # Handle duplicate slug - find existing entity and add to mapping.
                error_msg = str(e.orig).lower()
                if ('ix_entity_revisions_slug_current_unique' in error_msg or
                    'unique constraint failed: entity_revisions.slug' in error_msg):
                    warning = f"Skipping duplicate entity slug: {slug}"
                    warnings.append(warning)
                    logger.warning(warning)

                    # Find the existing entity so we can still create relations to it
                    stmt = select(EntityRevision).where(
                        EntityRevision.slug == slug,
                        EntityRevision.is_current == True
                    )
                    result = await self.db.execute(stmt)
                    existing_revision = result.scalar_one_or_none()
                    if existing_revision:
                        entity_mapping[extracted.slug] = existing_revision.entity_id

                    continue
                else:
                    raise
            except Exception as e:
                logger.error("Failed to create entity '%s' in bulk operation: %s", slug, e, exc_info=True)
                raise

        logger.info(
            "Bulk created %d entities, skipped %d duplicates",
            len(entity_mapping),
            len(warnings),
        )

        return entity_mapping, warnings

    async def bulk_create_relations(
        self,
        relations: list[ExtractedRelation],
        entity_mapping: SlugEntityMap,
        source_id: UUID,
        user_id: UUID | None = None
    ) -> tuple[list[ExtractedRelation], list[UUID], list[str]]:
        """
        Bulk create relations with their first revisions and role revisions.

        Resolves subject/object slugs to entity IDs using provided mapping.
        Creates Relation, RelationRevision, and RoleRevisions atomically.

        Args:
            relations: List of extracted relations to create
            entity_mapping: Dict mapping entity slug -> entity_id (from bulk_create_entities)
            source_id: Source ID to associate with relations
            user_id: User creating the relations (for provenance)

        Returns:
            Tuple of (created ExtractedRelation list, created relation ID list,
            list of warning strings describing skipped relations)

        Raises:
            Exception: On database errors
        """
        created_relations: list[ExtractedRelation] = []
        relation_ids: list[UUID] = []
        warnings = []

        # Process relations one at a time using savepoints (begin_nested) so a single
        # failure only rolls back that relation, leaving all others intact.
        for extracted in relations:
            # NEW: Resolve ALL entity slugs in roles array (N-ary relations)
            resolved_roles = []
            missing_entities = []

            for role in extracted.roles:
                entity_id = entity_mapping.get(role.entity_slug)

                if not entity_id:
                    missing_entities.append(role.entity_slug)
                else:
                    resolved_roles.append({
                        'entity_id': entity_id,
                        'entity_slug': role.entity_slug,
                        'role_type': role.role_type
                    })

            # Skip relation if ANY entity is missing
            if missing_entities:
                warning = f"Skipping relation {extracted.relation_type}: missing entities {missing_entities}"
                warnings.append(warning)
                logger.warning(warning)
                continue

            # Need at least 2 entities for a relation
            if len(resolved_roles) < 2:
                warning = f"Skipping relation {extracted.relation_type}: only {len(resolved_roles)} entities (need ≥2)"
                warnings.append(warning)
                logger.warning(warning)
                continue

            try:
                async with self.db.begin_nested():
                    # Create base relation
                    relation = Relation(source_id=source_id)
                    self.db.add(relation)
                    await self.db.flush()  # Get relation.id

                    # Prepare revision data
                    # Map extraction schema to database schema
                    revision_data = {
                        "kind": extracted.relation_type,  # "treats", "causes", etc.
                        "direction": _build_relation_direction(extracted),
                        "confidence": CONFIDENCE_FLOAT.get(extracted.confidence, CONFIDENCE_FLOAT["low"]),
                        "scope": _build_relation_scope(extracted),
                        "notes": {"en": extracted.notes} if extracted.notes else None,
                        "created_with_llm": settings.OPENAI_MODEL,
                        "created_by_user_id": user_id,
                        # LLM-created revisions start as drafts pending human review
                        "status": "draft",
                        "llm_review_status": "pending_review",
                    }

                    # Create first revision
                    revision = await create_new_revision(
                        db=self.db,
                        revision_class=RelationRevision,
                        parent_id_field='relation_id',
                        parent_id=relation.id,
                        revision_data=revision_data,
                        set_as_current=True,
                    )

                    # Create role revisions for ALL entities in the relation (N-ary support)
                    # Each resolved role becomes a RelationRoleRevision
                    for role_data in resolved_roles:
                        role_revision = RelationRoleRevision(
                            relation_revision_id=revision.id,
                            entity_id=role_data['entity_id'],
                            role_type=role_data['role_type'],  # Semantic role (agent, target, population, etc.)
                            weight=1.0,  # Default weight (can be adjusted based on evidence)
                            coverage=None,  # No coverage for individual roles
                        )
                        self.db.add(role_revision)

                    logger.debug(
                        f"Created relation {extracted.relation_type} with {len(resolved_roles)} roles: "
                        f"{[r['role_type'] for r in resolved_roles]}"
                    )

                    created_relations.append(extracted)
                    relation_ids.append(relation.id)

            except IntegrityError as e:
                # Savepoint was already rolled back; outer transaction is intact.
                # Treat DB constraint violations as skippable (e.g. duplicate FK).
                role_summary = " + ".join([f"{r['entity_slug']}({r['role_type']})" for r in resolved_roles[:3]])
                warning = f"Skipping relation {extracted.relation_type} [{role_summary}]: integrity error: {str(e.orig)}"
                warnings.append(warning)
                logger.warning(warning)
                continue
            except Exception as e:
                logger.error(
                    "Unexpected error creating relation %s: %s",
                    extracted.relation_type,
                    e,
                    exc_info=True,
                )
                raise

        logger.info(
            "Bulk created %d relations, skipped %d with errors/missing entities",
            len(relation_ids),
            len(warnings),
        )

        return created_relations, relation_ids, warnings
