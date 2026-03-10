from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from typing import Optional, Tuple
from uuid import UUID

from app.schemas.entity import EntityWrite, EntityRead
from app.schemas.filters import EntityFilters, EntityFilterOptions, UICategoryOption, ClinicalEffectOption
from app.repositories.entity_repo import EntityRepository
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.mappers.entity_mapper import (
    entity_revision_from_write,
    entity_to_read,
)
from app.utils.revision_helpers import get_current_revision, create_new_revision
from app.services.derived_properties_service import DerivedPropertiesService
from app.services.entity_query_builder import EntityQueryBuilder
from app.utils.errors import EntityNotFoundException, ValidationException, ErrorCode


class EntityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EntityRepository(db)
        self.query_builder = EntityQueryBuilder(db)

    async def create(self, payload: EntityWrite, user_id: UUID | None = None) -> EntityRead:
        """
        Create a new entity with its first revision.

        Creates both:
        1. Base Entity (immutable, just id + created_at)
        2. EntityRevision (all the data)

        Raises:
            HTTPException 409: If an entity with this slug already exists
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

        except IntegrityError as e:
            await self.db.rollback()
            # Check if it's a duplicate slug error (both PostgreSQL and SQLite)
            error_msg = str(e.orig).lower()
            if ('ix_entity_revisions_slug_current_unique' in error_msg or
                'unique constraint failed: entity_revisions.slug' in error_msg):
                raise ValidationException(
                    message="Entity slug already exists",
                    field="slug",
                    details=f"An entity with slug '{payload.slug}' already exists",
                    context={"slug": payload.slug}
                )
            # Re-raise other integrity errors
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def get(self, entity_id: UUID) -> EntityRead:
        """Get entity with its current revision."""
        entity = await self.repo.get_by_id(entity_id)
        if not entity:
            raise EntityNotFoundException(
                entity_id=str(entity_id)
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
        - clinical_effects: Filter by relation types (advanced)
        - consensus_level: Filter by consensus level (advanced)
        - evidence_quality_min/max: Filter by average trust level (advanced)
        - recency: Filter by most recent source year (advanced)
        - limit: Maximum number of results to return
        - offset: Number of results to skip

        Returns:
            Tuple of (items, total_count)
        """
        # Build the complete query using the query builder
        base_query = self.query_builder.build_query(filters)

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

    async def update(self, entity_id: str, payload: EntityWrite, user_id: UUID | None = None) -> EntityRead:
        """
        Update an entity by creating a new revision.

        The base Entity remains immutable. This creates a new EntityRevision
        with is_current=True and marks the old revision as is_current=False.
        """
        try:
            # Verify entity exists
            entity = await self.repo.get_by_id(entity_id)
            if not entity:
                raise EntityNotFoundException(
                    entity_id=str(entity_id)
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

        except (EntityNotFoundException, ValidationException):
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
                raise EntityNotFoundException(
                    entity_id=str(entity_id)
                )

            # Delete the entity (cascade should handle revisions)
            await self.repo.delete(entity)
            await self.db.commit()

        except EntityNotFoundException:
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def get_filter_options(self) -> EntityFilterOptions:
        """
        Get available filter options for entities.

        Returns distinct UI categories with i18n labels using efficient database queries.
        This avoids fetching all entity records when populating filter UI controls.

        Returns:
            EntityFilterOptions with available ui_categories and advanced options
        """
        from app.models.ui_category import UiCategory

        # Get all UI categories with their i18n labels
        category_query = select(UiCategory.id, UiCategory.labels).order_by(UiCategory.order)
        category_result = await self.db.execute(category_query)
        categories = category_result.all()

        ui_categories = [
            UICategoryOption(id=str(cat_id), label=labels)
            for cat_id, labels in categories
        ]

        # Get advanced filter options using derived properties service
        derived_service = DerivedPropertiesService(self.db)

        # Get clinical effects (relation types)
        import json as json_module

        clinical_effects_data = await derived_service.get_all_clinical_effects()
        clinical_effects = [
            ClinicalEffectOption(
                type_id=effect["type_id"],
                label=json_module.loads(effect["label"]) if isinstance(effect["label"], str) else effect["label"]
            )
            for effect in clinical_effects_data
        ] if clinical_effects_data else None

        # Get evidence quality range
        evidence_quality_range = await derived_service.get_evidence_quality_range()

        # Get year range from sources that have relations with entities
        year_range = await derived_service.get_entity_year_range()

        return EntityFilterOptions(
            ui_categories=ui_categories,
            clinical_effects=clinical_effects,
            consensus_levels=["strong", "moderate", "weak", "disputed"],
            evidence_quality_range=evidence_quality_range,
            recency_options=["recent", "older", "historical"],
            year_range=year_range,
        )