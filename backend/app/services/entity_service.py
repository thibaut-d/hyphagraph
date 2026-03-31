import asyncio
import logging

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
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.ui_category import UiCategory
from app.mappers.entity_mapper import (
    entity_revision_from_write,
    entity_to_read,
)
from app.utils.revision_helpers import get_current_revision, create_new_revision
from app.services.derived_properties_service import DerivedPropertiesService
from app.services.entity_query_builder import EntityQueryBuilder
from app.utils.errors import AppException, EntityNotFoundException, ValidationException, ErrorCode

logger = logging.getLogger(__name__)


class EntityService:
    def __init__(
        self,
        db: AsyncSession,
        derived_properties_service: DerivedPropertiesService | None = None,
    ):
        self.db = db
        self.repo = EntityRepository(db)
        self.query_builder = EntityQueryBuilder(db)
        self.derived_properties_service = derived_properties_service or DerivedPropertiesService(db)

    @staticmethod
    def _raise_if_slug_conflict(e: IntegrityError, slug: str) -> None:
        """Re-raise e as a structured 409 if it is a slug uniqueness violation."""
        error_msg = str(e.orig).lower()
        if ('ix_entity_revisions_slug_current_unique' in error_msg or
                'unique constraint failed: entity_revisions.slug' in error_msg):
            raise AppException(
                status_code=409,
                error_code=ErrorCode.ENTITY_SLUG_CONFLICT,
                message="Entity slug already exists",
                field="slug",
                details=f"An entity with slug '{slug}' already exists",
                context={"slug": slug},
            )
        raise e

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
            if not user_id:
                logger.warning("Creating entity revision without user attribution (user_id=None) for slug=%s", payload.slug)
            else:
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
            self._raise_if_slug_conflict(e, payload.slug)
        except Exception as e:
            logger.error("Failed to create entity '%s': %s", payload.slug, e, exc_info=True)
            await self.db.rollback()
            raise

    async def get(self, entity_id: UUID) -> EntityRead:
        """Get entity with its current revision and computed consensus level."""
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
        if current_revision is None or current_revision.status != "confirmed":
            raise EntityNotFoundException(entity_id=str(entity_id))

        result = entity_to_read(entity, current_revision)
        result.consensus_level = await self.derived_properties_service.get_entity_consensus_level(entity.id)
        return result

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

    async def update(self, entity_id: UUID, payload: EntityWrite, user_id: UUID | None = None) -> EntityRead:
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
            if not user_id:
                logger.warning("Updating entity revision without user attribution (user_id=None) for entity_id=%s", entity_id)
            else:
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
        except IntegrityError as e:
            await self.db.rollback()
            self._raise_if_slug_conflict(e, payload.slug)
        except Exception as e:
            logger.error("Failed to update entity %s: %s", entity_id, e, exc_info=True)
            await self.db.rollback()
            raise

    async def delete(self, entity_id: UUID) -> None:
        """
        Delete an entity and all its revisions.

        Raises 409 if any current relation revisions reference this entity,
        so callers must remove those relations first.
        """
        try:
            entity = await self.repo.get_by_id(entity_id)
            if not entity:
                raise EntityNotFoundException(
                    entity_id=str(entity_id)
                )

            # Block deletion if ANY relation revision (current or historical) references
            # this entity.  Historical revisions are immutable snapshots — cascade-deleting
            # their RelationRoleRevision rows would silently destroy audit history.
            rel_count_result = await self.db.execute(
                select(func.count(func.distinct(RelationRevision.relation_id)))
                .join(RelationRoleRevision, RelationRoleRevision.relation_revision_id == RelationRevision.id)
                .where(RelationRoleRevision.entity_id == entity.id)
            )
            rel_count = rel_count_result.scalar() or 0
            if rel_count > 0:
                raise AppException(
                    status_code=409,
                    error_code=ErrorCode.ENTITY_HAS_RELATIONS,
                    message="Entity has dependent relations",
                    details=(
                        f"This entity is referenced by {rel_count} relation(s) "
                        "(including historical revisions). "
                        "Delete those relations before deleting the entity."
                    ),
                    context={"relation_count": rel_count},
                )

            # Delete the entity (cascade handles revisions)
            await self.repo.delete(entity)
            await self.db.commit()

        except (EntityNotFoundException, AppException):
            raise
        except Exception as e:
            logger.error("Failed to delete entity %s: %s", entity_id, e, exc_info=True)
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
        # Get all UI categories with their i18n labels
        category_query = select(UiCategory.id, UiCategory.labels).order_by(UiCategory.order)
        category_result = await self.db.execute(category_query)
        categories = category_result.all()

        ui_categories = [
            UICategoryOption(id=str(cat_id), label=labels)
            for cat_id, labels in categories
        ]

        # Run the three aggregation queries in parallel (DF-ENT-M1)
        clinical_effects_data, evidence_quality_range, year_range = await asyncio.gather(
            self.derived_properties_service.get_all_clinical_effects(),
            self.derived_properties_service.get_evidence_quality_range(),
            self.derived_properties_service.get_entity_year_range(),
        )

        clinical_effects = [
            ClinicalEffectOption(type_id=kind, label={"en": kind})
            for kind in (clinical_effects_data or [])
        ]

        return EntityFilterOptions(
            ui_categories=ui_categories,
            clinical_effects=clinical_effects,
            consensus_levels=["strong", "moderate", "weak", "disputed"],
            evidence_quality_range=evidence_quality_range,
            recency_options=["recent", "older", "historical"],
            year_range=year_range,
        )
