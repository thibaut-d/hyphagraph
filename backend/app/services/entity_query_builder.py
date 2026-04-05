"""
Entity Query Builder - Constructs complex SQLAlchemy queries for entity filtering.

This module extracts the query building logic from EntityService.list_all()
into focused, testable methods following the Query Builder pattern.
"""
from sqlalchemy import Select, select, or_, func, and_, distinct, case
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.schemas.filters import EntityFilters
from app.services.query_predicates import canonical_relation_predicate


class EntityQueryBuilder:
    """
    Builds SQLAlchemy queries for entity filtering and searching.

    Provides a clean separation between query construction and business logic,
    making the code more maintainable and testable.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the query builder.

        Args:
            db: The async database session
        """
        self.db = db

    def build_base_query(self) -> Select:
        """
        Create the base SELECT statement for entities with their current revisions.

        Returns:
            Base SQLAlchemy Select query joining Entity and EntityRevision
        """
        return (
            select(Entity, EntityRevision)
            .join(EntityRevision, Entity.id == EntityRevision.entity_id)
            .where(EntityRevision.is_current == True)
            .where(EntityRevision.status == "confirmed")
            .where(Entity.is_rejected == False)
            .where(Entity.is_merged == False)  # NEW-MRG-M1
        )

    def apply_basic_filters(self, query: Select, filters: EntityFilters) -> Select:
        """
        Apply simple filters: ui_category_id, search, and status.

        Args:
            query: The base query to filter
            filters: Filter criteria to apply

        Returns:
            Modified query with basic filters applied
        """
        # Filter by UI category (OR logic)
        if filters.ui_category_id:
            # Convert string UUIDs to UUID objects
            category_uuids = [UUID(cat_id) for cat_id in filters.ui_category_id]
            query = query.where(EntityRevision.ui_category_id.in_(category_uuids))

        # Search in slug (case-insensitive)
        if filters.search:
            search_term = f"%{filters.search.lower()}%"
            query = query.where(EntityRevision.slug.ilike(search_term))

        return query

    def add_clinical_effects_filter(self, query: Select, filters: EntityFilters) -> Select:
        """
        Add clinical effects subquery filter.

        Filters entities that have relations of specified types.

        Args:
            query: The base query to filter
            filters: Filter criteria containing clinical_effects

        Returns:
            Modified query with clinical effects filter applied
        """
        if not filters.clinical_effects:
            return query

        # Entities that have relations of these types
        clinical_effects_subquery = (
            select(distinct(RelationRoleRevision.entity_id))
            .join(RelationRevision, RelationRoleRevision.relation_revision_id == RelationRevision.id)
            .where(
                and_(
                    canonical_relation_predicate(),
                    RelationRevision.kind.in_(filters.clinical_effects)
                )
            )
        )
        return query.where(Entity.id.in_(clinical_effects_subquery))

    def add_evidence_quality_filter(self, query: Select, filters: EntityFilters) -> Select:
        """
        Add evidence quality aggregation filter.

        Filters by average trust level from sources.

        Args:
            query: The base query to filter
            filters: Filter criteria containing evidence_quality_min/max

        Returns:
            Modified query with evidence quality filter applied
        """
        if filters.evidence_quality_min is None and filters.evidence_quality_max is None:
            return query

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
            .where(canonical_relation_predicate())
            .group_by(RelationRoleRevision.entity_id)
            .subquery()
        )

        # Join with the average trust subquery
        query = query.join(
            avg_trust_subquery,
            Entity.id == avg_trust_subquery.c.entity_id
        )

        if filters.evidence_quality_min is not None:
            query = query.where(avg_trust_subquery.c.avg_trust >= filters.evidence_quality_min)
        if filters.evidence_quality_max is not None:
            query = query.where(avg_trust_subquery.c.avg_trust <= filters.evidence_quality_max)

        return query

    def add_recency_filter(self, query: Select, filters: EntityFilters) -> Select:
        """
        Add recency computation filter.

        Filters by most recent source year based on recency categories:
        - recent: Last 5 years
        - older: 5-10 years ago
        - historical: More than 10 years ago

        Args:
            query: The base query to filter
            filters: Filter criteria containing recency options

        Returns:
            Modified query with recency filter applied
        """
        if not filters.recency:
            return query

        current_year = datetime.now().year

        # Subquery to get max year per entity.
        # COALESCE(MAX(year), 0): entities whose every source has NULL year
        # are treated as "historical" (year 0) rather than silently excluded
        # by NULL comparisons.  Entities with no relations at all are absent
        # from this subquery; the OUTER JOIN below leaves max_year as NULL,
        # making all recency conditions evaluate to NULL/false — correct
        # behaviour (no source data → excluded from recency filter).
        max_year_subquery = (
            select(
                RelationRoleRevision.entity_id,
                func.coalesce(func.max(SourceRevision.year), 0).label('max_year')
            )
            .select_from(RelationRoleRevision)
            .join(RelationRevision, RelationRoleRevision.relation_revision_id == RelationRevision.id)
            .join(Relation, RelationRevision.relation_id == Relation.id)
            .join(Source, Relation.source_id == Source.id)
            .join(SourceRevision, and_(
                SourceRevision.source_id == Source.id,
                SourceRevision.is_current == True
            ))
            .where(canonical_relation_predicate())
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
            query = query.outerjoin(
                max_year_subquery,
                Entity.id == max_year_subquery.c.entity_id
            ).where(or_(*recency_filter_conditions))

        return query

    def add_consensus_filter(self, query: Select, filters: EntityFilters) -> Select:
        """
        Add consensus level computation filter.

        Consensus is based on disagreement ratio: contradicts_count / total_count
        Levels:
        - strong: <10% disagreement
        - moderate: 10-30% disagreement
        - weak: 30-50% disagreement
        - disputed: >50% disagreement

        Args:
            query: The base query to filter
            filters: Filter criteria containing consensus_level

        Returns:
            Modified query with consensus filter applied
        """
        if not filters.consensus_level:
            return query

        # Subquery to compute disagreement ratio per entity
        consensus_subquery = (
            select(
                RelationRoleRevision.entity_id,
                func.count().label('total_relations'),
                func.sum(
                    case(
                        (RelationRevision.direction == "contradicts", 1),
                        else_=0
                    )
                ).label('contradicts_count')
            )
            .select_from(RelationRoleRevision)
            .join(RelationRevision, RelationRoleRevision.relation_revision_id == RelationRevision.id)
            .where(RelationRevision.is_current == True)
            .group_by(RelationRoleRevision.entity_id)
            .subquery()
        )

        # Build consensus level conditions
        # disagreement_ratio = contradicts_count / total_relations
        consensus_conditions = []
        for level in filters.consensus_level:
            if level == "strong":
                # <10% disagreement
                consensus_conditions.append(
                    consensus_subquery.c.contradicts_count < (consensus_subquery.c.total_relations * 0.10)
                )
            elif level == "moderate":
                # 10-30% disagreement
                consensus_conditions.append(and_(
                    consensus_subquery.c.contradicts_count >= (consensus_subquery.c.total_relations * 0.10),
                    consensus_subquery.c.contradicts_count < (consensus_subquery.c.total_relations * 0.30)
                ))
            elif level == "weak":
                # 30-50% disagreement
                consensus_conditions.append(and_(
                    consensus_subquery.c.contradicts_count >= (consensus_subquery.c.total_relations * 0.30),
                    consensus_subquery.c.contradicts_count < (consensus_subquery.c.total_relations * 0.50)
                ))
            elif level == "disputed":
                # >50% disagreement
                consensus_conditions.append(
                    consensus_subquery.c.contradicts_count >= (consensus_subquery.c.total_relations * 0.50)
                )

        if consensus_conditions:
            query = query.join(
                consensus_subquery,
                Entity.id == consensus_subquery.c.entity_id
            ).where(or_(*consensus_conditions))

        return query

    def build_query(self, filters: Optional[EntityFilters] = None) -> Select:
        """
        Orchestrate all query building steps.

        Builds the complete query by applying all filters in the correct order.

        Args:
            filters: Optional filter criteria to apply

        Returns:
            Complete SQLAlchemy Select query ready for execution
        """
        # Start with base query
        query = self.build_base_query()

        # Apply filters if provided
        if filters:
            query = self.apply_basic_filters(query, filters)
            query = self.add_clinical_effects_filter(query, filters)
            query = self.add_evidence_quality_filter(query, filters)
            query = self.add_recency_filter(query, filters)
            query = self.add_consensus_filter(query, filters)

        return query
