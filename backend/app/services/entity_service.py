from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from fastapi import HTTPException, status
from typing import Optional
from uuid import UUID

from app.schemas.entity import EntityWrite, EntityRead
from app.schemas.filters import EntityFilters
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

    async def list_all(self, filters: Optional[EntityFilters] = None) -> list[EntityRead]:
        """
        List all entities with their current revisions, optionally filtered.

        Filters are applied to the current revision data:
        - ui_category_id: Filter by UI category (OR logic)
        - search: Case-insensitive search in slug
        """
        # Build query for entities with their current revisions
        query = (
            select(Entity, EntityRevision)
            .join(EntityRevision, Entity.id == EntityRevision.entity_id)
            .where(EntityRevision.is_current == True)
        )

        # Apply filters if provided
        if filters:
            # Filter by UI category (OR logic)
            if filters.ui_category_id:
                # Convert string UUIDs to UUID objects
                category_uuids = [UUID(cat_id) for cat_id in filters.ui_category_id]
                query = query.where(EntityRevision.ui_category_id.in_(category_uuids))

            # Search in slug (case-insensitive)
            if filters.search:
                search_term = f"%{filters.search.lower()}%"
                query = query.where(EntityRevision.slug.ilike(search_term))

        # Execute query
        result_rows = await self.db.execute(query)
        results = result_rows.all()

        # Convert to EntityRead objects
        return [entity_to_read(entity, revision) for entity, revision in results]

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