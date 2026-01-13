"""
Derived Properties Service - Compute aggregated properties for entities and sources.

This service provides computed/derived properties that require aggregation across relations,
sources, and inferences. These are used for advanced filtering in the UI.

Performance Note:
- These queries involve JOINs and aggregations, so they may be slower than simple filters
- Consider caching results if performance becomes an issue
- Filters are for UI display only and don't affect inference calculations
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, distinct, and_, or_
from uuid import UUID
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from app.models.entity import Entity
from app.models.source import Source
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.source_revision import SourceRevision
from app.models.computed_relation import ComputedRelation
from app.models.relation_type import RelationType


class DerivedPropertiesService:
    """Service for computing derived/aggregated properties for filtering."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # Entity-level derived properties
    # =========================================================================

    async def get_entity_clinical_effects(self, entity_id: UUID) -> List[str]:
        """
        Get clinical effects for an entity (what it does).

        Returns relation types where this entity participates
        (e.g., "treats", "causes", "prevents").

        Args:
            entity_id: Entity UUID

        Returns:
            List of relation type IDs (e.g., ["treats", "causes"])
        """
        # Get all relation types where this entity is involved
        query = (
            select(distinct(RelationType.type_id))
            .join(RelationRoleRevision, RelationType.type_id == RelationRoleRevision.relation_type_id)
            .join(RelationRevision, RelationRoleRevision.relation_revision_id == RelationRevision.id)
            .where(
                and_(
                    RelationRevision.is_current == True,
                    RelationRoleRevision.entity_id == entity_id,
                )
            )
        )

        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

    async def get_entity_consensus_level(self, entity_id: UUID) -> str:
        """
        Calculate consensus level for an entity based on relation agreement.

        Consensus levels:
        - "strong": <10% disagreement in directions
        - "moderate": 10-30% disagreement
        - "weak": 30-50% disagreement
        - "disputed": >50% disagreement

        Disagreement is measured by relations with contradictory directions
        about the same entity.

        Args:
            entity_id: Entity UUID

        Returns:
            Consensus level: "strong", "moderate", "weak", or "disputed"
        """
        # Count relations by direction for this entity
        query = (
            select(
                RelationRevision.direction,
                func.count().label('count')
            )
            .join(RelationRoleRevision, RelationRevision.id == RelationRoleRevision.relation_revision_id)
            .where(
                and_(
                    RelationRevision.is_current == True,
                    RelationRoleRevision.entity_id == entity_id,
                )
            )
            .group_by(RelationRevision.direction)
        )

        result = await self.db.execute(query)
        direction_counts = {row.direction: row.count for row in result.all()}

        total = sum(direction_counts.values())
        if total == 0:
            return "unknown"

        # Calculate disagreement: contradictory relations vs total
        contradicts_count = direction_counts.get("contradicts", 0)
        disagreement_ratio = contradicts_count / total

        if disagreement_ratio < 0.10:
            return "strong"
        elif disagreement_ratio < 0.30:
            return "moderate"
        elif disagreement_ratio < 0.50:
            return "weak"
        else:
            return "disputed"

    async def get_entity_evidence_quality(self, entity_id: UUID) -> Optional[float]:
        """
        Calculate average evidence quality (trust level) for an entity.

        Computes the average trust_level of all sources that have relations
        involving this entity.

        Args:
            entity_id: Entity UUID

        Returns:
            Average trust level (0.0-1.0) or None if no sources
        """
        query = (
            select(func.avg(SourceRevision.trust_level))
            .select_from(Source)
            .join(SourceRevision, Source.id == SourceRevision.source_id)
            .join(Relation, Source.id == Relation.source_id)
            .join(RelationRevision, Relation.id == RelationRevision.relation_id)
            .join(RelationRoleRevision, RelationRevision.id == RelationRoleRevision.relation_revision_id)
            .where(
                and_(
                    SourceRevision.is_current == True,
                    RelationRevision.is_current == True,
                    RelationRoleRevision.entity_id == entity_id,
                )
            )
        )

        result = await self.db.execute(query)
        avg_trust = result.scalar()
        return float(avg_trust) if avg_trust is not None else None

    async def get_entity_recency(self, entity_id: UUID) -> Optional[int]:
        """
        Get the most recent source year for an entity.

        Returns the maximum publication year of sources that cite this entity.

        Args:
            entity_id: Entity UUID

        Returns:
            Most recent year or None if no sources
        """
        query = (
            select(func.max(SourceRevision.year))
            .select_from(Source)
            .join(SourceRevision, Source.id == SourceRevision.source_id)
            .join(Relation, Source.id == Relation.source_id)
            .join(RelationRevision, Relation.id == RelationRevision.relation_id)
            .join(RelationRoleRevision, RelationRevision.id == RelationRoleRevision.relation_revision_id)
            .where(
                and_(
                    SourceRevision.is_current == True,
                    RelationRevision.is_current == True,
                    RelationRoleRevision.entity_id == entity_id,
                )
            )
        )

        result = await self.db.execute(query)
        max_year = result.scalar()
        return int(max_year) if max_year is not None else None

    # =========================================================================
    # Source-level derived properties
    # =========================================================================

    async def get_source_role_in_graph(self, source_id: UUID) -> str:
        """
        Determine a source's role in the knowledge graph.

        Roles:
        - "pillar": >5 relations (heavily cited)
        - "supporting": 2-5 relations (moderately cited)
        - "contradictory": Has contradictory direction relations
        - "single": 1 relation only

        Args:
            source_id: Source UUID

        Returns:
            Role: "pillar", "supporting", "contradictory", or "single"
        """
        # Count relations and check for contradictory ones
        query = (
            select(
                func.count(distinct(Relation.id)).label('relation_count'),
                func.sum(
                    case(
                        (RelationRevision.direction == "contradicts", 1),
                        else_=0
                    )
                ).label('contradictory_count')
            )
            .select_from(Relation)
            .join(RelationRevision, Relation.id == RelationRevision.relation_id)
            .where(
                and_(
                    Relation.source_id == source_id,
                    RelationRevision.is_current == True,
                )
            )
        )

        result = await self.db.execute(query)
        row = result.first()

        if not row or row.relation_count == 0:
            return "none"

        relation_count = row.relation_count
        has_contradictory = (row.contradictory_count or 0) > 0

        if has_contradictory:
            return "contradictory"
        elif relation_count > 5:
            return "pillar"
        elif relation_count >= 2:
            return "supporting"
        else:
            return "single"

    async def get_source_domain(self, source_id: UUID) -> Optional[str]:
        """
        Infer the medical domain of a source from journal name or content.

        This is a simplified implementation that uses keyword matching on journal names.
        A more sophisticated implementation could use:
        - Journal categorization databases
        - Keyword extraction from titles/abstracts
        - Machine learning classification

        Args:
            source_id: Source UUID

        Returns:
            Domain string (e.g., "cardiology", "neurology") or None
        """
        # Get source origin (journal name)
        query = (
            select(SourceRevision.origin, SourceRevision.title)
            .where(
                and_(
                    SourceRevision.source_id == source_id,
                    SourceRevision.is_current == True,
                )
            )
        )

        result = await self.db.execute(query)
        row = result.first()

        if not row:
            return None

        origin = (row.origin or "").lower()
        title = (row.title or "").lower()
        combined = f"{origin} {title}"

        # Simple keyword-based domain inference
        # This should be expanded based on actual medical domains in your data
        domain_keywords = {
            "cardiology": ["cardio", "heart", "cardiac", "cardiovascular"],
            "neurology": ["neuro", "brain", "neural", "cognitive"],
            "psychiatry": ["psychiatry", "mental", "psychology", "behavioral"],
            "oncology": ["cancer", "oncology", "tumor", "carcinoma"],
            "endocrinology": ["endocrine", "diabetes", "hormone", "metabolic"],
            "immunology": ["immune", "immunology", "antibody", "vaccine"],
            "gastroenterology": ["gastro", "digestive", "intestinal", "gi"],
            "nephrology": ["kidney", "renal", "nephrology"],
            "pulmonology": ["lung", "respiratory", "pulmonary"],
            "rheumatology": ["rheumat", "arthritis", "autoimmune"],
        }

        for domain, keywords in domain_keywords.items():
            if any(keyword in combined for keyword in keywords):
                return domain

        return "general"

    # =========================================================================
    # Bulk operations for filter options
    # =========================================================================

    async def get_all_clinical_effects(self) -> List[Dict[str, str]]:
        """
        Get all unique clinical effects (relation types) in the graph.

        Returns:
            List of dicts with type_id and label for each effect
        """
        query = (
            select(
                RelationType.type_id,
                RelationType.label
            )
            .where(RelationType.is_active == True)
            .order_by(RelationType.usage_count.desc())
        )

        result = await self.db.execute(query)
        return [
            {"type_id": row.type_id, "label": row.label}
            for row in result.all()
        ]

    async def get_evidence_quality_range(self) -> Optional[Tuple[float, float]]:
        """
        Get the range of average evidence quality across all entities.

        Returns:
            Tuple of (min, max) average trust levels or None
        """
        # This is expensive - compute per-entity average trust levels
        # For now, return the global range of source trust levels
        query = select(
            func.min(SourceRevision.trust_level),
            func.max(SourceRevision.trust_level)
        ).where(SourceRevision.is_current == True)

        result = await self.db.execute(query)
        row = result.first()

        if row and row[0] is not None and row[1] is not None:
            return (float(row[0]), float(row[1]))

        return None

    async def get_recency_range(self) -> Optional[Tuple[int, int]]:
        """
        Get the range of source years across all entities.

        Returns:
            Tuple of (min_year, max_year) or None
        """
        query = select(
            func.min(SourceRevision.year),
            func.max(SourceRevision.year)
        ).where(SourceRevision.is_current == True)

        result = await self.db.execute(query)
        row = result.first()

        if row and row[0] is not None and row[1] is not None:
            return (int(row[0]), int(row[1]))

        return None

    async def get_all_domains(self) -> List[str]:
        """
        Get all unique domains inferred from sources.

        This is a simplified implementation that returns predefined domains.
        A production version would compute actual domains from source metadata.

        Returns:
            List of domain strings
        """
        # For now, return standard medical domains
        # A better implementation would scan all sources and extract actual domains
        return [
            "cardiology",
            "neurology",
            "psychiatry",
            "oncology",
            "endocrinology",
            "immunology",
            "gastroenterology",
            "nephrology",
            "pulmonology",
            "rheumatology",
            "general",
        ]

    async def count_sources_by_role(self) -> Dict[str, int]:
        """
        Count sources by their role in the graph.

        Returns:
            Dict mapping role to count
        """
        # This is expensive - would need to compute role for each source
        # For MVP, return estimate based on relation counts
        query = (
            select(
                Relation.source_id,
                func.count(distinct(Relation.id)).label('relation_count')
            )
            .join(RelationRevision, Relation.id == RelationRevision.relation_id)
            .where(RelationRevision.is_current == True)
            .group_by(Relation.source_id)
        )

        result = await self.db.execute(query)

        role_counts = {
            "pillar": 0,
            "supporting": 0,
            "single": 0,
            "none": 0,
        }

        for row in result.all():
            count = row.relation_count
            if count > 5:
                role_counts["pillar"] += 1
            elif count >= 2:
                role_counts["supporting"] += 1
            else:
                role_counts["single"] += 1

        return role_counts
