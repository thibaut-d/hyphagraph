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
    ) -> dict[str, UUID]:
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
        entity_mapping = {}
        warnings = []

        # Process entities one at a time with individual transactions
        # This allows us to skip duplicates without breaking the session
        for extracted in entities:
            try:
                # Create base entity
                entity = Entity()
                self.db.add(entity)
                await self.db.flush()  # Get entity.id

                # Prepare revision data
                revision_data = {
                    "slug": extracted.slug,
                    "summary": extracted.summary,
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

                # Don't commit here - will commit at transaction end to avoid greenlet issues
                # await self.db.commit()  # REMOVED - commit happens at endpoint level

                # Map slug to entity_id
                entity_mapping[extracted.slug] = entity.id

            except IntegrityError as e:
                # Handle duplicate slug - find existing entity and add to mapping
                error_msg = str(e.orig).lower()
                if ('ix_entity_revisions_slug_current_unique' in error_msg or
                    'unique constraint failed: entity_revisions.slug' in error_msg):
                    warning = f"Skipping duplicate entity slug: {extracted.slug}"
                    warnings.append(warning)
                    logger.warning(warning)
                    await self.db.rollback()

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
                    # Re-raise other integrity errors
                    await self.db.rollback()
                    raise
            except Exception:
                # Rollback on any other error
                await self.db.rollback()
                raise

        logger.info(
            f"Bulk created {len(entity_mapping)} entities, "
            f"skipped {len(warnings)} duplicates"
        )

        return entity_mapping

    async def bulk_create_relations(
        self,
        relations: list[ExtractedRelation],
        entity_mapping: dict[str, UUID],
        source_id: UUID,
        user_id: UUID | None = None
    ) -> list[UUID]:
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
        relation_ids = []
        warnings = []

        # Process relations one at a time with individual transactions
        # This ensures session stays clean even if individual relations fail
        for extracted in relations:
            # Resolve subject and object entity IDs
            subject_id = entity_mapping.get(extracted.subject_slug)
            object_id = entity_mapping.get(extracted.object_slug)

            # Skip relation if either entity is missing
            if not subject_id:
                warning = f"Skipping relation: subject '{extracted.subject_slug}' not in mapping"
                warnings.append(warning)
                logger.warning(warning)
                continue

            if not object_id:
                warning = f"Skipping relation: object '{extracted.object_slug}' not in mapping"
                warnings.append(warning)
                logger.warning(warning)
                continue

            try:
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

                # Create role revisions (subject and object)
                # Subject role
                subject_role = RelationRoleRevision(
                    relation_revision_id=revision.id,
                    entity_id=subject_id,
                    role_type="subject",
                    weight=1.0,  # Default weight
                    coverage=None,  # No coverage for subject
                )
                self.db.add(subject_role)

                # Object role
                object_role = RelationRoleRevision(
                    relation_revision_id=revision.id,
                    entity_id=object_id,
                    role_type="object",
                    weight=1.0,  # Default weight
                    coverage=None,  # No coverage for object
                )
                self.db.add(object_role)

                # Add contextual roles if present
                if extracted.roles:
                    # Dosage role
                    if extracted.roles.get("dosage"):
                        # For now, store dosage in notes (would need entity resolution for proper linking)
                        pass

                    # Population role (if entity exists in mapping)
                    if extracted.roles.get("population"):
                        pop_slug = extracted.roles["population"]
                        pop_id = entity_mapping.get(pop_slug)
                        if pop_id:
                            pop_role = RelationRoleRevision(
                                relation_revision_id=revision.id,
                                entity_id=pop_id,
                                role_type="population",
                                weight=1.0,
                                coverage=None,
                            )
                            self.db.add(pop_role)

                # Don't commit here - will commit at transaction end to avoid greenlet issues
                # await self.db.commit()  # REMOVED - commit happens at endpoint level

                relation_ids.append(relation.id)

            except Exception as e:
                # Rollback this relation and continue
                warning = f"Skipping relation {extracted.subject_slug}--{extracted.relation_type}-->{extracted.object_slug}: {str(e)}"
                warnings.append(warning)
                logger.warning(warning)
                await self.db.rollback()
                continue

        logger.info(
            f"Bulk created {len(relation_ids)} relations, "
            f"skipped {len(warnings)} with errors/missing entities"
        )

        return relation_ids
