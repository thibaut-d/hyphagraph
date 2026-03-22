import logging
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.relation import RelationWrite, RelationRead
from app.repositories.relation_repo import RelationRepository
from app.repositories.computed_relation_repo import ComputedRelationRepository
from app.models.entity import Entity
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.mappers.relation_mapper import (
    relation_revision_from_write,
    relation_to_read,
)
from app.services.validation_service import validate_relation
from app.utils.revision_helpers import get_current_revision, create_new_revision
from app.utils.errors import RelationNotFoundException, ValidationException
from app.services.inference.read_models import resolve_entity_slugs

logger = logging.getLogger(__name__)


class RelationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RelationRepository(db)

    async def _validate_entity_ids(self, roles) -> None:
        """Raise ValidationException if any role references a non-existent entity."""
        entity_ids = [role_data.entity_id for role_data in roles]
        result = await self.db.execute(
            select(Entity.id).where(Entity.id.in_(entity_ids))
        )
        found_ids = {row[0] for row in result.all()}
        for role_data in roles:
            if role_data.entity_id not in found_ids:
                raise ValidationException(
                    message="Entity not found",
                    field="roles",
                    details=f"Entity with ID '{role_data.entity_id}' does not exist",
                    context={"entity_id": str(role_data.entity_id)},
                )

    async def create(self, payload: RelationWrite, user_id: UUID | None = None) -> RelationRead:
        """
        Create a new relation with its first revision.

        Creates:
        1. Base Relation (immutable, just id + created_at + source_id)
        2. RelationRevision (all mutable data)
        3. RelationRoleRevisions (roles tied to this revision)
        """
        # 1. Structural validation
        validate_relation(payload)
        await self._validate_entity_ids(payload.roles)

        try:
            # 2. Create base relation
            relation = Relation(source_id=payload.source_id)
            self.db.add(relation)
            await self.db.flush()  # Get the relation.id

            # 3. Create first revision
            revision_data = relation_revision_from_write(payload)
            if not user_id:
                logger.warning("Creating relation revision without user attribution (user_id=None)")
            else:
                revision_data['created_by_user_id'] = user_id

            revision = await create_new_revision(
                db=self.db,
                revision_class=RelationRevision,
                parent_id_field='relation_id',
                parent_id=relation.id,
                revision_data=revision_data,
                set_as_current=True,
            )

            # 4. Create role revisions (snapshot of roles for this revision)
            for role_data in payload.roles:
                role_revision = RelationRoleRevision(
                    relation_revision_id=revision.id,
                    entity_id=role_data.entity_id,
                    role_type=role_data.role_type,
                    weight=role_data.weight,
                    coverage=role_data.coverage,
                )
                self.db.add(role_revision)

            await self.db.flush()  # Ensure roles are created

            # 5. Invalidate inference cache for all affected entities
            computed_repo = ComputedRelationRepository(self.db)
            for entity_id in {role_data.entity_id for role_data in payload.roles}:
                await computed_repo.delete_by_entity_id(entity_id)

            # 6. Commit transaction
            await self.db.commit()

            # 7. Refresh to get the roles relationship populated
            await self.db.refresh(revision, ['roles'])

            # 8. Resolve entity slugs for display
            entity_ids = {role.entity_id for role in revision.roles}
            entity_slug_map = await resolve_entity_slugs(self.db, entity_ids)

            # 9. Return Read
            return relation_to_read(relation, revision, entity_slug_map=entity_slug_map)

        except Exception as e:
            logger.error("Failed to create relation for source %s: %s", payload.source_id, e, exc_info=True)
            await self.db.rollback()
            raise

    async def get(self, relation_id) -> RelationRead:
        """Get relation with its current revision."""
        relation = await self.repo.get_by_id(relation_id)
        if not relation:
            raise RelationNotFoundException(
                relation_id=str(relation_id)
            )

        # Get current revision with roles eagerly loaded
        current_revision = await get_current_revision(
            db=self.db,
            revision_class=RelationRevision,
            parent_id_field='relation_id',
            parent_id=relation.id,
            load_relationships=['roles'],
        )

        entity_ids = {role.entity_id for role in current_revision.roles}
        entity_slug_map = await resolve_entity_slugs(self.db, entity_ids)
        return relation_to_read(relation, current_revision, entity_slug_map=entity_slug_map)

    async def list_by_source(self, source_id: str | UUID) -> list[RelationRead]:
        """List all relations for a source with their current revisions."""
        if isinstance(source_id, str):
            source_id = UUID(source_id)
        relations = await self.repo.list_by_source(source_id)

        # The repo eagerly loads Relation.revisions + RelationRevision.roles.
        # Filter to the current revision in Python to avoid N+1 queries.
        revisions = []
        for relation in relations:
            current_revision = next(
                (r for r in relation.revisions if r.is_current), None
            )
            if current_revision is None:
                logger.warning("Relation %s has no current revision, skipping", relation.id)
                continue
            revisions.append((relation, current_revision))

        # Resolve entity slugs in one batch query
        entity_ids = {
            role.entity_id
            for _, revision in revisions
            for role in revision.roles
        }
        entity_slug_map = await resolve_entity_slugs(self.db, entity_ids)

        return [
            relation_to_read(relation, revision, entity_slug_map=entity_slug_map)
            for relation, revision in revisions
        ]

    async def update(self, relation_id: UUID, payload: RelationWrite, user_id: UUID | None = None) -> RelationRead:
        """
        Update a relation by creating a new revision.

        The base Relation remains immutable. This creates a new RelationRevision
        with is_current=True and marks the old revision as is_current=False.

        Note: The source_id in the base Relation cannot be changed.
        """
        # 1. Structural validation (no DB)
        validate_relation(payload)

        try:
            # 2. Verify relation exists
            relation = await self.repo.get_by_id(relation_id)
            if not relation:
                raise RelationNotFoundException(
                    relation_id=str(relation_id)
                )

            # Verify source_id hasn't changed (immutable; check before DB entity lookup)
            if payload.source_id != relation.source_id:
                raise ValidationException(
                    message="Cannot change source_id of existing relation",
                    field="source_id",
                    details="The source_id field is immutable and cannot be changed after creation",
                    context={"relation_id": str(relation_id), "current_source_id": str(relation.source_id), "attempted_source_id": str(payload.source_id)}
                )

            # 3. Validate referenced entity IDs exist
            await self._validate_entity_ids(payload.roles)

            # 4. Capture old entity IDs for cache invalidation before revision changes
            old_revision = await get_current_revision(
                db=self.db,
                revision_class=RelationRevision,
                parent_id_field='relation_id',
                parent_id=relation.id,
                load_relationships=['roles'],
            )
            old_entity_ids = {role.entity_id for role in old_revision.roles}

            # 5. Create new revision with updated data
            revision_data = relation_revision_from_write(payload)
            if not user_id:
                logger.warning("Updating relation revision without user attribution (user_id=None) for relation_id=%s", relation_id)
            else:
                revision_data['created_by_user_id'] = user_id

            revision = await create_new_revision(
                db=self.db,
                revision_class=RelationRevision,
                parent_id_field='relation_id',
                parent_id=relation.id,
                revision_data=revision_data,
                set_as_current=True,
            )

            # 4. Create role revisions (snapshot of roles for this revision)
            for role_data in payload.roles:
                role_revision = RelationRoleRevision(
                    relation_revision_id=revision.id,
                    entity_id=role_data.entity_id,
                    role_type=role_data.role_type,
                    weight=role_data.weight,
                    coverage=role_data.coverage,
                )
                self.db.add(role_revision)

            await self.db.flush()  # Ensure roles are created

            # 5. Invalidate inference cache for old and new entity IDs
            computed_repo = ComputedRelationRepository(self.db)
            all_affected_entity_ids = old_entity_ids | {role_data.entity_id for role_data in payload.roles}
            for entity_id in all_affected_entity_ids:
                await computed_repo.delete_by_entity_id(entity_id)

            # 6. Commit transaction
            await self.db.commit()

            # 7. Refresh to get the roles relationship populated
            await self.db.refresh(revision, ['roles'])

            # 8. Resolve entity slugs for display
            entity_ids = {role.entity_id for role in revision.roles}
            entity_slug_map = await resolve_entity_slugs(self.db, entity_ids)

            # 9. Return Read
            return relation_to_read(relation, revision, entity_slug_map=entity_slug_map)

        except (RelationNotFoundException, ValidationException):
            raise
        except Exception as e:
            logger.error("Failed to update relation %s: %s", relation_id, e, exc_info=True)
            await self.db.rollback()
            raise

    async def delete(self, relation_id: UUID) -> None:
        """
        Delete a relation and all its revisions.

        Note: This is a hard delete. Consider implementing soft delete
        by adding a deleted_at field if needed.
        """
        try:
            relation = await self.repo.get_by_id(relation_id)
            if not relation:
                raise RelationNotFoundException(
                    relation_id=str(relation_id)
                )

            # Capture entity IDs from ALL revisions before deleting — the cascade
            # will remove all revisions, not just the current one.  An entity that
            # appeared in a historical revision may still have stale ComputedRelations.
            all_entity_ids_stmt = (
                select(RelationRoleRevision.entity_id)
                .join(RelationRevision, RelationRoleRevision.relation_revision_id == RelationRevision.id)
                .where(RelationRevision.relation_id == relation.id)
            )
            all_entity_ids_result = await self.db.execute(all_entity_ids_stmt)
            entity_ids_to_invalidate = {row[0] for row in all_entity_ids_result.all()}

            # Delete the relation (cascade should handle revisions and role revisions)
            await self.repo.delete(relation)

            # Invalidate inference cache for all affected entities
            computed_repo = ComputedRelationRepository(self.db)
            for entity_id in entity_ids_to_invalidate:
                await computed_repo.delete_by_entity_id(entity_id)

            await self.db.commit()

        except RelationNotFoundException:
            raise
        except Exception as e:
            logger.error("Failed to delete relation %s: %s", relation_id, e, exc_info=True)
            await self.db.rollback()
            raise