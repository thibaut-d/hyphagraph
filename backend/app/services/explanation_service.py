"""
Explainability service for computed inferences.

Provides detailed explanations of why an inference has a specific score,
which sources contributed, and how they agree or disagree.
"""

from collections import defaultdict
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.inference_service import InferenceService
from app.schemas.inference import InferenceRead, RoleInference
from app.schemas.relation import RelationRead
from app.schemas.explanation import (
    ExplanationRead,
    SourceContribution,
    ConfidenceFactor,
    ContradictionDetail,
)
from app.repositories.relation_repo import RelationRepository
from app.repositories.source_repo import SourceRepository


class ExplanationService:
    """Service for generating detailed explanations of computed inferences."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.inference_service = InferenceService(db)
        self.relation_repo = RelationRepository(db)
        self.source_repo = SourceRepository(db)

    async def explain_inference(
        self,
        entity_id: UUID,
        role_type: str,
        scope_filter: Optional[Dict[str, Any]] = None,
    ) -> ExplanationRead:
        """
        Generate comprehensive explanation for a role inference.

        Args:
            entity_id: Entity to explain inference for
            role_type: Role to explain (e.g., "drug", "condition")
            scope_filter: Optional scope filter (same as inference API)

        Returns:
            Detailed explanation with source chain, confidence breakdown, contradictions

        Raises:
            ValueError: If role_type not found in computed inference
        """
        # 1. Compute inference (reuse existing service)
        inference = await self.inference_service.infer_for_entity(
            entity_id, scope_filter
        )

        # 2. Find the specific role inference
        role_inference = self._find_role_inference(inference, role_type)
        if not role_inference:
            raise ValueError(
                f"Role type '{role_type}' not found in computed inference"
            )

        # 3. Get contributing relations
        contributing_relations = self._get_contributing_relations(
            inference.relations_by_kind, role_type
        )

        # 4. Build natural language summary
        summary = self._generate_summary(
            role_inference, contributing_relations, role_type
        )

        # 5. Build confidence breakdown
        confidence_factors = self._build_confidence_breakdown(
            role_inference, contributing_relations
        )

        # 6. Identify contradictions
        contradictions = self._identify_contradictions(
            contributing_relations, role_type, role_inference.disagreement
        )

        # 7. Build source chain
        source_chain = await self._build_source_chain(
            contributing_relations, role_type
        )

        return ExplanationRead(
            entity_id=entity_id,
            role_type=role_type,
            score=role_inference.score,
            confidence=role_inference.confidence,
            disagreement=role_inference.disagreement,
            summary=summary,
            confidence_factors=confidence_factors,
            contradictions=contradictions,
            source_chain=source_chain,
            scope_filter=scope_filter,
        )

    def _find_role_inference(
        self, inference: InferenceRead, role_type: str
    ) -> Optional[RoleInference]:
        """Find the specific role inference from computed results."""
        for role_inf in inference.role_inferences:
            if role_inf.role_type == role_type:
                return role_inf
        return None

    def _get_contributing_relations(
        self,
        relations_by_kind: Dict[str, List[RelationRead]],
        role_type: str,
    ) -> List[RelationRead]:
        """
        Extract relations that contribute to this role type.

        Args:
            relations_by_kind: Grouped relations from inference
            role_type: Role to filter by

        Returns:
            List of relations that have this role type
        """
        contributing = []

        for kind, relations in relations_by_kind.items():
            for relation in relations:
                # Check if this relation has the role type
                if relation.roles:
                    has_role = any(r.role_type == role_type for r in relation.roles)
                    if has_role:
                        contributing.append(relation)

        return contributing

    def _generate_summary(
        self,
        role_inference: RoleInference,
        contributing_relations: List[RelationRead],
        role_type: str,
    ) -> str:
        """
        Generate natural language summary of the inference.

        Example outputs:
        - "Based on 5 sources, this shows a strong positive effect (score: 0.75)
          with high confidence (92%). One source contradicts this finding."
        - "Based on 2 sources, this shows a weak negative effect (score: -0.25)
          with moderate confidence (65%). No contradictions detected."
        """
        num_sources = len(contributing_relations)
        score = role_inference.score
        confidence = role_inference.confidence
        disagreement = role_inference.disagreement

        # Determine direction
        if score is None:
            direction = "no clear indication"
        elif score > 0.5:
            direction = "a strong positive effect"
        elif score > 0.0:
            direction = "a weak positive effect"
        elif score == 0.0:
            direction = "a neutral effect"
        elif score > -0.5:
            direction = "a weak negative effect"
        else:
            direction = "a strong negative effect"

        # Determine confidence level
        if confidence > 0.8:
            conf_level = "high"
        elif confidence > 0.5:
            conf_level = "moderate"
        else:
            conf_level = "low"

        # Score display
        score_display = f"{score:.2f}" if score is not None else "N/A"

        # Base summary
        source_word = "source" if num_sources == 1 else "sources"
        summary = (
            f"Based on {num_sources} {source_word}, "
            f"this '{role_type}' shows {direction} (score: {score_display}) "
            f"with {conf_level} confidence ({confidence * 100:.0f}%)."
        )

        # Add contradiction note
        if disagreement > 0.5:
            summary += " Significant contradictions detected among sources."
        elif disagreement > 0.2:
            summary += " Some contradictions detected among sources."
        else:
            summary += " No significant contradictions detected."

        return summary

    def _build_confidence_breakdown(
        self,
        role_inference: RoleInference,
        contributing_relations: List[RelationRead],
    ) -> List[ConfidenceFactor]:
        """
        Build breakdown of confidence contributors.

        Explains why confidence is X% based on:
        - Coverage (number of sources)
        - Trust levels
        - Agreement vs disagreement
        """
        factors = []

        # Coverage factor
        coverage = role_inference.coverage
        factors.append(
            ConfidenceFactor(
                factor="Coverage",
                value=coverage,
                explanation=f"Total information coverage from {len(contributing_relations)} sources",
            )
        )

        # Confidence calculation (exponential saturation)
        # Formula: 1 - exp(-λ * coverage)
        factors.append(
            ConfidenceFactor(
                factor="Confidence",
                value=role_inference.confidence,
                explanation=f"Confidence based on coverage (exponential saturation model)",
            )
        )

        # Disagreement factor
        if role_inference.disagreement > 0:
            factors.append(
                ConfidenceFactor(
                    factor="Disagreement",
                    value=role_inference.disagreement,
                    explanation=f"Measure of contradiction between sources (higher = more disagreement)",
                )
            )

        # Trust levels (if available)
        trust_levels = [
            r.source_trust for r in contributing_relations if r.source_trust is not None
        ]
        if trust_levels:
            avg_trust = sum(trust_levels) / len(trust_levels)
            factors.append(
                ConfidenceFactor(
                    factor="Average Source Trust",
                    value=avg_trust,
                    explanation=f"Average trust level across {len(trust_levels)} rated sources",
                )
            )

        return factors

    def _identify_contradictions(
        self,
        contributing_relations: List[RelationRead],
        role_type: str,
        disagreement: float,
    ) -> Optional[ContradictionDetail]:
        """
        Identify and detail contradictory sources.

        Groups sources by direction (positive vs negative contribution)
        to show which sources support vs contradict the inference.
        """
        if disagreement < 0.1:
            # No significant contradictions
            return None

        supporting = []
        contradicting = []

        for relation in contributing_relations:
            # Get the role weight for this role type
            role = next(
                (r for r in (relation.roles or []) if r.role_type == role_type),
                None,
            )

            if role and role.weight is not None:
                # Positive weight = supporting, negative = contradicting
                target_list = supporting if role.weight > 0 else contradicting

                # We'll build SourceContribution objects in _build_source_chain
                # For now, just track the relation
                target_list.append(relation)

        # Only return contradiction detail if we have both supporting and contradicting
        if supporting and contradicting:
            # Will be filled in _build_source_chain
            return ContradictionDetail(
                supporting_sources=[],
                contradicting_sources=[],
                disagreement_score=disagreement,
            )

        return None

    async def _build_source_chain(
        self,
        contributing_relations: List[RelationRead],
        role_type: str,
    ) -> List[SourceContribution]:
        """
        Build complete source chain with provenance.

        For each contributing relation:
        - Source metadata (title, authors, year, URL, trust)
        - Relation details (kind, direction, confidence, scope)
        - Role contribution weight
        - Contribution percentage

        Returns:
            List of SourceContribution objects sorted by contribution percentage
        """
        source_chain = []
        total_weight = 0.0

        # Calculate total weight for percentage calculations
        for relation in contributing_relations:
            role = next(
                (r for r in (relation.roles or []) if r.role_type == role_type),
                None,
            )
            if role and role.weight is not None:
                total_weight += abs(role.weight) * (relation.confidence or 1.0)

        # Build source contributions
        for relation in contributing_relations:
            # Get role weight
            role = next(
                (r for r in (relation.roles or []) if r.role_type == role_type),
                None,
            )

            if not role or role.weight is None:
                continue

            # Calculate contribution percentage
            relation_weight = abs(role.weight) * (relation.confidence or 1.0)
            contribution_pct = (
                (relation_weight / total_weight * 100) if total_weight > 0 else 0
            )

            # Determine direction
            direction = "supports" if role.weight > 0 else "contradicts"

            source_chain.append(
                SourceContribution(
                    # Source metadata
                    source_id=relation.source_id,
                    source_title=relation.source_title or "Unknown",
                    source_authors=relation.source_authors,
                    source_year=relation.source_year,
                    source_kind=relation.source_kind or "unknown",
                    source_trust=relation.source_trust,
                    source_url=relation.source_url or "#",
                    # Relation metadata
                    relation_id=relation.id,
                    relation_kind=relation.kind or "unknown",
                    relation_direction=direction,
                    relation_confidence=relation.confidence or 1.0,
                    relation_scope=relation.scope,
                    # Contribution analysis
                    role_weight=role.weight,
                    contribution_percentage=contribution_pct,
                )
            )

        # Sort by contribution percentage (descending)
        source_chain.sort(key=lambda x: x.contribution_percentage, reverse=True)

        return source_chain
