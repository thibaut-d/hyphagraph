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
from app.utils.revision_helpers import create_new_revision
from app.config import settings

logger = logging.getLogger(__name__)


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
        source_id: UUID,
        user_id: UUID | None = None
    ) -> SlugEntityMap:
        """
        Bulk create entities with their first revisions.

        Creates both base Entity and EntityRevision for each entity in a
        single transaction. Handles duplicate slug errors by skipping and logging.

        Args:
            entities: List of extracted entities to create
            source_id: Source ID to associate with entities
            user_id: User creating the entities (for provenance)

        Returns:
            Dict mapping entity slug -> entity_id for successfully created entities

        Raises:
            Exception: On database errors other than duplicate slugs
        """
        entity_mapping: SlugEntityMap = {}
        warnings = []

        # Process entities one at a time using savepoints (begin_nested) so a duplicate-slug error
        # only rolls back that single entity, leaving all others intact.
        for extracted in entities:
            try:
                async with self.db.begin_nested():
                    # Create base entity
                    entity = Entity()
                    self.db.add(entity)
                    await self.db.flush()  # Get entity.id

                    # Prepare revision data
                    revision_data = {
                        "slug": extracted.slug,
                        "summary": {"en": extracted.summary} if extracted.summary else None,
                        "ui_category_id": None,  # Will be set by frontend/user later
                        "created_with_llm": settings.OPENAI_MODEL,  # Track LLM provenance
                        "created_by_user_id": user_id,
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
                    warning = f"Skipping duplicate entity slug: {extracted.slug}"
                    warnings.append(warning)
                    logger.warning(warning)

                    # Find the existing entity so we can still create relations to it
                    stmt = select(EntityRevision).where(
                        EntityRevision.slug == extracted.slug,
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
                logger.error("Failed to create entity '%s' in bulk operation: %s", extracted.slug, e, exc_info=True)
                raise

        logger.info(
            f"Bulk created {len(entity_mapping)} entities, "
            f"skipped {len(warnings)} duplicates"
        )

        return entity_mapping

    async def bulk_create_relations(
        self,
        relations: list[ExtractedRelation],
        entity_mapping: SlugEntityMap,
        source_id: UUID,
        user_id: UUID | None = None
    ) -> tuple[list[ExtractedRelation], list[UUID]]:
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
            List of created relation IDs

        Raises:
            ValueError: If subject/object slug not found in entity_mapping
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
                        "confidence": 0.8 if extracted.confidence == "high" else 0.6 if extracted.confidence == "medium" else 0.4,
                        "notes": {"en": extracted.notes} if extracted.notes else None,
                        "created_with_llm": settings.OPENAI_MODEL,
                        "created_by_user_id": user_id,
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

            except Exception as e:
                # Savepoint was already rolled back; outer transaction is intact.
                role_summary = " + ".join([f"{r['entity_slug']}({r['role_type']})" for r in resolved_roles[:3]])
                warning = f"Skipping relation {extracted.relation_type} [{role_summary}]: {str(e)}"
                warnings.append(warning)
                logger.warning(warning)
                continue

        logger.info(
            f"Bulk created {len(relation_ids)} relations, "
            f"skipped {len(warnings)} with errors/missing entities"
        )

        return created_relations, relation_ids
