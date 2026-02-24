from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, and_, distinct
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from typing import Optional, Tuple
from uuid import UUID
from datetime import datetime

from app.schemas.entity import EntityWrite, EntityRead
from app.schemas.filters import EntityFilters, EntityFilterOptions, UICategoryOption, ClinicalEffectOption
from app.repositories.entity_repo import EntityRepository
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.mappers.entity_mapper import (
    entity_revision_from_write,
    entity_to_read,
)
from app.utils.revision_helpers import get_current_revision, create_new_revision
from app.services.derived_properties_service import DerivedPropertiesService


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
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"An entity with slug '{payload.slug}' already exists"
                )
            # Re-raise other integrity errors
            raise
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
        - clinical_effects: Filter by relation types (advanced)
        - consensus_level: Filter by consensus level (advanced)
        - evidence_quality_min/max: Filter by average trust level (advanced)
        - recency: Filter by most recent source year (advanced)
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

        # Apply basic filters if provided
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

            # === Advanced Filters (require aggregations) ===

            # Filter by clinical effects (relation types)
            if filters.clinical_effects:
                # Entities that have relations of these types
                clinical_effects_subquery = (
                    select(distinct(RelationRoleRevision.entity_id))
                    .join(RelationRevision, RelationRoleRevision.relation_revision_id == RelationRevision.id)
                    .where(
                        and_(
                            RelationRevision.is_current == True,
                            RelationRoleRevision.relation_type_id.in_(filters.clinical_effects)
                        )
                    )
                )
                base_query = base_query.where(Entity.id.in_(clinical_effects_subquery))

            # Filter by evidence quality (average trust level)
            if filters.evidence_quality_min is not None or filters.evidence_quality_max is not None:
                # Subquery to compute average trust level per entity
                avg_trust_subquery = (
                    select(
                        RelationRoleRevision.entity_id,
                        func.avg(SourceRevision.trust_level).label('avg_trust')
                    )
                    .select_from(RelationRoleRevision)
                    .join(RelationRevision, RelationRoleRevision.relation_revision_id == RelationRevision.id)
                    .join(Relation, RelationRevision.relation_id == Relation.id)
                    .join(Source, Relation.source_id == Source.id)
                    .join(SourceRevision, and_(
                        SourceRevision.source_id == Source.id,
                        SourceRevision.is_current == True
                    ))
                    .where(RelationRevision.is_current == True)
                    .group_by(RelationRoleRevision.entity_id)
                    .subquery()
                )

                # Join with the average trust subquery
                base_query = base_query.join(
                    avg_trust_subquery,
                    Entity.id == avg_trust_subquery.c.entity_id
                )

                if filters.evidence_quality_min is not None:
                    base_query = base_query.where(avg_trust_subquery.c.avg_trust >= filters.evidence_quality_min)
                if filters.evidence_quality_max is not None:
                    base_query = base_query.where(avg_trust_subquery.c.avg_trust <= filters.evidence_quality_max)

            # Filter by recency (most recent source year)
            if filters.recency:
                current_year = datetime.now().year

                # Build recency conditions
                recency_conditions = []
                for recency_value in filters.recency:
                    if recency_value == "recent":
                        # Last 5 years
                        recency_conditions.append(current_year - 5)
                    elif recency_value == "older":
                        # 5-10 years ago
                        recency_conditions.append(current_year - 10)
                    elif recency_value == "historical":
                        # More than 10 years ago
                        recency_conditions.append(0)  # All years

                # Subquery to get max year per entity
                if recency_conditions:
                    max_year_subquery = (
                        select(
                            RelationRoleRevision.entity_id,
                            func.max(SourceRevision.year).label('max_year')
                        )
                        .select_from(RelationRoleRevision)
                        .join(RelationRevision, RelationRoleRevision.relation_revision_id == RelationRevision.id)
                        .join(Relation, RelationRevision.relation_id == Relation.id)
                        .join(Source, Relation.source_id == Source.id)
                        .join(SourceRevision, and_(
                            SourceRevision.source_id == Source.id,
                            SourceRevision.is_current == True
                        ))
                        .where(RelationRevision.is_current == True)
                        .group_by(RelationRoleRevision.entity_id)
                        .subquery()
                    )

                    # Build OR conditions for recency
                    recency_filter_conditions = []
                    if "recent" in filters.recency:
                        recency_filter_conditions.append(max_year_subquery.c.max_year >= current_year - 5)
                    if "older" in filters.recency:
                        recency_filter_conditions.append(and_(
                            max_year_subquery.c.max_year >= current_year - 10,
                            max_year_subquery.c.max_year < current_year - 5
                        ))
                    if "historical" in filters.recency:
                        recency_filter_conditions.append(max_year_subquery.c.max_year < current_year - 10)

                    if recency_filter_conditions:
                        base_query = base_query.join(
                            max_year_subquery,
                            Entity.id == max_year_subquery.c.entity_id
                        ).where(or_(*recency_filter_conditions))

            # Filter by consensus level
            # Note: This is expensive as it requires computing consensus for each entity
            # For MVP, we skip this filter or implement it post-query
            # TODO: Implement consensus level filter with proper indexing
            if filters.consensus_level:
                # This would require computing disagreement ratio per entity
                # For now, we'll implement this as a post-filter in a future iteration
                pass

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

        # Post-filter by consensus level if needed (expensive but accurate)
        if filters and filters.consensus_level:
            derived_service = DerivedPropertiesService(self.db)
            filtered_items = []
            for item in items:
                consensus = await derived_service.get_entity_consensus_level(UUID(item.id))
                if consensus in filters.consensus_level:
                    filtered_items.append(item)
            items = filtered_items
            total = len(items)  # Update total after filtering

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

        return EntityFilterOptions(
            ui_categories=ui_categories,
            clinical_effects=clinical_effects,
            consensus_levels=["strong", "moderate", "weak", "disputed"],
            evidence_quality_range=evidence_quality_range,
            recency_options=["recent", "older", "historical"],
            year_range=None,  # TODO: Implement year range from related sources
        )