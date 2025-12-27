from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.entity import EntityWrite, EntityRead
from app.repositories.entity_repo import EntityRepository
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.mappers.entity_mapper import (
    entity_revision_from_write,
    entity_to_read,
)
from app.utils.revision_helpers import get_current_revision, create_new_revision


class EntityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EntityRepository(db)

    async def create(self, payload: EntityWrite, user_id=None) -> EntityRead:
        """
        Create a new entity with its first revision.

        Creates both:
        1. Base Entity (immutable, just id + created_at)
        2. EntityRevision (all the data)
        """
        try:
            # Create base entity
            entity = Entity()
            self.db.add(entity)
            await self.db.flush()  # Get the entity.id

            # Create first revision
            revision_data = entity_revision_from_write(payload)
            if user_id:
                revision_data['created_by_user_id'] = user_id

            revision = await create_new_revision(
                db=self.db,
                revision_class=EntityRevision,
                parent_id_field='entity_id',
                parent_id=entity.id,
                revision_data=revision_data,
                set_as_current=True,
            )

            await self.db.commit()
            return entity_to_read(entity, revision)

        except Exception:
            await self.db.rollback()
            raise

    async def get(self, entity_id) -> EntityRead:
        """Get entity with its current revision."""
        entity = await self.repo.get_by_id(entity_id)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entity not found",
            )

        # Get current revision
        current_revision = await get_current_revision(
            db=self.db,
            revision_class=EntityRevision,
            parent_id_field='entity_id',
            parent_id=entity.id,
        )

        return entity_to_read(entity, current_revision)

    async def list_all(self) -> list[EntityRead]:
        """List all entities with their current revisions."""
        entities = await self.repo.list_all()

        # Get current revisions for all entities
        result = []
        for entity in entities:
            current_revision = await get_current_revision(
                db=self.db,
                revision_class=EntityRevision,
                parent_id_field='entity_id',
                parent_id=entity.id,
            )
            result.append(entity_to_read(entity, current_revision))

        return result

    async def update(self, entity_id: str, payload: EntityWrite, user_id=None) -> EntityRead:
        """
        Update an entity by creating a new revision.

        The base Entity remains immutable. This creates a new EntityRevision
        with is_current=True and marks the old revision as is_current=False.
        """
        try:
            # Verify entity exists
            entity = await self.repo.get_by_id(entity_id)
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Entity not found",
                )

            # Create new revision with updated data
            revision_data = entity_revision_from_write(payload)
            if user_id:
                revision_data['created_by_user_id'] = user_id

            revision = await create_new_revision(
                db=self.db,
                revision_class=EntityRevision,
                parent_id_field='entity_id',
                parent_id=entity.id,
                revision_data=revision_data,
                set_as_current=True,
            )

            await self.db.commit()
            return entity_to_read(entity, revision)

        except HTTPException:
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def delete(self, entity_id: str) -> None:
        """
        Delete an entity and all its revisions.

        Note: This is a hard delete. Consider implementing soft delete
        by adding a deleted_at field if needed.
        """
        try:
            entity = await self.repo.get_by_id(entity_id)
            if not entity:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Entity not found",
                )

            # Delete the entity (cascade should handle revisions)
            await self.repo.delete(entity)
            await self.db.commit()

        except HTTPException:
            raise
        except Exception:
            await self.db.rollback()
            raise