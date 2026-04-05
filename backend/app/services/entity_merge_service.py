"""
Entity Merge Service - Detect and merge duplicate entities.

Provides:
- Automatic duplicate detection (similar slugs, terms)
- Entity merging (move relations, add terms, soft delete)
- Entity terms management for aliases
"""
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, update, func
from difflib import SequenceMatcher

from app.models.entity import Entity
from app.models.entity_merge_record import EntityMergeRecord
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.repositories.computed_relation_repo import ComputedRelationRepository
from app.schemas.entity_merge import AutoMergeAction, EntityMergeResult


logger = logging.getLogger(__name__)


class EntityMergeService:
    """Service for detecting and merging duplicate entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_potential_duplicates(
        self,
        similarity_threshold: float = 0.8
    ) -> list[tuple[UUID, UUID, float]]:
        """
        Find pairs of entities that are likely duplicates.

        Uses:
        - Slug similarity (Levenshtein distance)
        - Term matching (check if one entity's slug matches another's terms)

        Returns:
            List of (entity_id_1, entity_id_2, similarity_score)
        """
        # Get all current entities
        stmt = select(Entity, EntityRevision).join(
            EntityRevision, Entity.id == EntityRevision.entity_id
        ).where(EntityRevision.is_current == True)

        result = await self.db.execute(stmt)
        entities = [(entity, revision) for entity, revision in result]

        duplicates = []

        # Compare each pair
        for i, (entity1, rev1) in enumerate(entities):
            for entity2, rev2 in entities[i + 1:]:
                # Calculate slug similarity
                similarity = SequenceMatcher(
                    None,
                    rev1.slug.lower(),
                    rev2.slug.lower()
                ).ratio()

                if similarity >= similarity_threshold:
                    duplicates.append((entity1.id, entity2.id, similarity))
                    logger.info(
                        f"Potential duplicate: {rev1.slug} vs {rev2.slug} "
                        f"(similarity: {similarity:.2f})"
                    )

        # Also check if one entity's slug matches another's terms
        stmt = select(EntityTerm)
        result = await self.db.execute(stmt)
        terms = result.scalars().all()

        for entity, revision in entities:
            for term in terms:
                if term.entity_id != entity.id:
                    # Check if this entity's slug matches another entity's term
                    if revision.slug.lower() == term.term.lower():
                        duplicates.append((entity.id, term.entity_id, 1.0))
                        logger.info(
                            f"Slug matches term: {revision.slug} = term of entity {term.entity_id}"
                        )

        return duplicates

    async def merge_entities(
        self,
        source_entity_id: UUID,
        target_entity_id: UUID,
        preserve_source_slug_as_term: bool = True,
        merged_by_user_id: UUID | None = None,
    ) -> EntityMergeResult:
        """
        Merge source entity into target entity.

        Process:
        1. Move all relation_role_revisions from source to target
        2. Add source entity's slug as term to target entity
        3. Mark source entity as merged (soft delete)

        Args:
            source_entity_id: Entity to merge (will be disabled)
            target_entity_id: Entity to merge into (will receive relations)
            preserve_source_slug_as_term: Add source slug to target's terms

        Returns:
            Statistics about the merge
        """
        # Guard: self-merge is invalid (DF-MRG-M1)
        if source_entity_id == target_entity_id:
            raise ValueError("Cannot merge entity with itself: source and target must be different entities")

        # Guard: check for circular merge — reject if either entity already appears
        # as a source in an existing merge record involving the other (DF-MRG-C1)
        circular_stmt = select(EntityMergeRecord).where(
            EntityMergeRecord.source_entity_id.in_([source_entity_id, target_entity_id]),
            EntityMergeRecord.target_entity_id.in_([source_entity_id, target_entity_id]),
        )
        circular_result = await self.db.execute(circular_stmt)
        if circular_result.scalar_one_or_none():
            raise ValueError(
                "Circular merge detected: one of these entities has already been merged into the other"
            )

        # Get source and target entities
        stmt = select(Entity, EntityRevision).join(
            EntityRevision, Entity.id == EntityRevision.entity_id
        ).where(
            EntityRevision.is_current == True,
            Entity.id.in_([source_entity_id, target_entity_id])
        )

        result = await self.db.execute(stmt)
        entities_map = {entity.id: (entity, revision) for entity, revision in result}

        if source_entity_id not in entities_map:
            raise ValueError(f"Source entity {source_entity_id} not found")
        if target_entity_id not in entities_map:
            raise ValueError(f"Target entity {target_entity_id} not found")

        _, source_revision = entities_map[source_entity_id]
        _, target_revision = entities_map[target_entity_id]

        logger.info(
            f"Merging entity '{source_revision.slug}' into '{target_revision.slug}'"
        )

        try:
            # Invalidate inference cache for both entities before moving roles (DF-MRG-M2).
            # Must happen before the UPDATE so the join-based lookup still finds the right rows.
            cache_repo = ComputedRelationRepository(self.db)
            await cache_repo.delete_by_entity_id(source_entity_id)
            await cache_repo.delete_by_entity_id(target_entity_id)

            # Count current-revision roles before merge (for result reporting)
            stmt = select(func.count()).select_from(RelationRoleRevision).where(
                RelationRoleRevision.entity_id == source_entity_id
            ).join(
                RelationRevision,
                RelationRoleRevision.relation_revision_id == RelationRevision.id,
            ).where(RelationRevision.is_current == True)  # noqa: E712
            result = await self.db.execute(stmt)
            relations_count = result.scalar()

            # Deduplicate participant collisions before rewriting remaining rows.
            # If the target entity already occupies the same role in a current revision,
            # keep the canonical target row and delete the source duplicate.
            duplicate_rows_stmt = (
                select(
                    RelationRoleRevision.id,
                    RelationRoleRevision.relation_revision_id,
                    RelationRoleRevision.role_type,
                )
                .join(
                    RelationRevision,
                    RelationRoleRevision.relation_revision_id == RelationRevision.id,
                )
                .where(
                    RelationRevision.is_current == True,  # noqa: E712
                    RelationRoleRevision.entity_id == source_entity_id,
                )
            )
            duplicate_rows = (await self.db.execute(duplicate_rows_stmt)).all()

            duplicate_source_role_ids: list[UUID] = []
            for role_row_id, relation_revision_id, role_type in duplicate_rows:
                target_role_stmt = select(RelationRoleRevision.id).where(
                    RelationRoleRevision.relation_revision_id == relation_revision_id,
                    RelationRoleRevision.entity_id == target_entity_id,
                    RelationRoleRevision.role_type == role_type,
                )
                target_role_id = (await self.db.execute(target_role_stmt)).scalar_one_or_none()
                if target_role_id is not None:
                    duplicate_source_role_ids.append(role_row_id)

            if duplicate_source_role_ids:
                await self.db.execute(
                    delete(RelationRoleRevision).where(
                        RelationRoleRevision.id.in_(duplicate_source_role_ids)
                    )
                )

            # Move roles from source to target — only in current revisions.
            # Historical revisions are immutable snapshots and must not be changed.
            current_revision_ids_stmt = (
                select(RelationRevision.id).where(RelationRevision.is_current == True)  # noqa: E712
            )
            await self.db.execute(
                update(RelationRoleRevision)
                .where(
                    RelationRoleRevision.entity_id == source_entity_id,
                    RelationRoleRevision.relation_revision_id.in_(current_revision_ids_stmt),
                )
                .values(entity_id=target_entity_id)
            )

            # Add source slug as term to target entity
            if preserve_source_slug_as_term:
                # Check if term already exists
                stmt = select(EntityTerm).where(
                    EntityTerm.entity_id == target_entity_id,
                    EntityTerm.term == source_revision.slug
                )
                result = await self.db.execute(stmt)
                existing_term = result.scalar_one_or_none()

                if not existing_term:
                    term = EntityTerm(
                        entity_id=target_entity_id,
                        term=source_revision.slug,
                        language="en",
                        display_order=None
                    )
                    self.db.add(term)

                    logger.info(f"Added term '{source_revision.slug}' to entity '{target_revision.slug}'")

            merge_record = EntityMergeRecord(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                merged_by_user_id=merged_by_user_id,
                source_slug=source_revision.slug,
                target_slug=target_revision.slug,
            )
            self.db.add(merge_record)

            # Mark source entity as merged.
            # Set is_merged=True on the Entity row so list/search/export queries
            # can filter it out efficiently. Also deactivate all revisions so
            # canonical-predicate joins find no current revision. (NEW-MRG-M1)
            await self.db.execute(
                update(Entity)
                .where(Entity.id == source_entity_id)
                .values(is_merged=True)
            )
            await self.db.execute(
                update(EntityRevision)
                .where(EntityRevision.entity_id == source_entity_id)
                .values(is_current=False)
            )

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

        logger.info(
            f"Merge complete: {relations_count} relations moved, "
            f"source entity marked as merged"
        )

        return EntityMergeResult(
            source_slug=source_revision.slug,
            target_slug=target_revision.slug,
            relations_moved=relations_count or 0,
            term_added=preserve_source_slug_as_term,
            merge_recorded=True,
        )

    async def auto_merge_obvious_duplicates(
        self,
        dry_run: bool = True
    ) -> list[AutoMergeAction]:
        """
        Automatically merge obvious duplicates.

        Obvious duplicates:
        - Same slug with suffix (fibromyalgia vs fibromyalgia-syndrome)
        - >90% similarity
        - One is subset of the other

        Args:
            dry_run: If True, only report duplicates without merging

        Returns:
            List of merge actions (performed or suggested)
        """
        duplicates = await self.find_potential_duplicates(similarity_threshold=0.9)
        merge_actions: list[AutoMergeAction] = []

        for source_id, target_id, similarity in duplicates:
            # Get slugs
            stmt = select(EntityRevision).where(
                EntityRevision.entity_id.in_([source_id, target_id]),
                EntityRevision.is_current == True
            )
            result = await self.db.execute(stmt)
            revisions = {rev.entity_id: rev for rev in result.scalars()}

            source_rev = revisions.get(source_id)
            target_rev = revisions.get(target_id)

            if not source_rev or not target_rev:
                continue

            # Determine which to keep (prefer shorter, simpler slug)
            if len(source_rev.slug) > len(target_rev.slug):
                # Keep target (shorter slug)
                action = AutoMergeAction(
                    source_slug=source_rev.slug,
                    target_slug=target_rev.slug,
                    similarity=similarity,
                    action="merge",
                )
            else:
                # Keep source (shorter slug)
                action = AutoMergeAction(
                    source_slug=target_rev.slug,
                    target_slug=source_rev.slug,
                    similarity=similarity,
                    action="merge",
                )

            if not dry_run:
                # Perform merge
                if len(source_rev.slug) > len(target_rev.slug):
                    result = await self.merge_entities(source_id, target_id)
                else:
                    result = await self.merge_entities(target_id, source_id)

                action.result = result

            merge_actions.append(action)

        logger.info(
            f"Auto-merge: {len(merge_actions)} duplicate pairs found"
            + (" (dry run)" if dry_run else " (merged)")
        )

        return merge_actions
