from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from fastapi import HTTPException, status
from typing import Optional, Tuple
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

    async def list_all(self, filters: Optional[EntityFilters] = None) -> Tuple[list[EntityRead], int]:
        """
        List all entities with their current revisions, optionally filtered and paginated.

        Filters are applied to the current revision data:
        - ui_category_id: Filter by UI category (OR logic)
        - search: Case-insensitive search in slug
        - limit: Maximum number of results to return
        - offset: Number of results to skip

        Returns:
            Tuple of (items, total_count)
        """
        # Build base query for entities with their current revisions
        base_query = (
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
                base_query = base_query.where(EntityRevision.ui_category_id.in_(category_uuids))

            # Search in slug (case-insensitive)
            if filters.search:
                search_term = f"%{filters.search.lower()}%"
                base_query = base_query.where(EntityRevision.slug.ilike(search_term))

        # Count total results before pagination
        count_query = select(func.count()).select_from(
            base_query.subquery()
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination to items query
        limit = filters.limit if filters else 50
        offset = filters.offset if filters else 0
        items_query = base_query.limit(limit).offset(offset)

        # Execute items query
        result_rows = await self.db.execute(items_query)
        results = result_rows.all()

        # Convert to EntityRead objects
        items = [entity_to_read(entity, revision) for entity, revision in results]

        return items, total

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