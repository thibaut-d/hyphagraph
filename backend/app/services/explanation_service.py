"""Explainability service for computed inferences."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.common_types import ScopeFilter
from app.services.inference_service import InferenceService
from app.services.source_service import SourceService
from app.schemas.inference import InferenceRead, RoleInference
from app.schemas.explanation import (
    ExplanationRead,
    SourceContribution,
    ConfidenceFactor,
    SummaryData,
)
from app.services.explanation_read_models import (
    attach_contradiction_sources,
    build_contradiction_detail,
)
from app.services.inference.evidence_views import RoleEvidenceRead


class ExplanationService:
    """Service for generating detailed explanations of computed inferences."""

    def __init__(
        self,
        db: AsyncSession,
        inference_service: Optional[InferenceService] = None,
        source_service: Optional[SourceService] = None,
    ):
        self.db = db
        shared_source_service = source_service or SourceService(db)
        self.source_service = shared_source_service
        self.inference_service = inference_service or InferenceService(
            db,
            source_service=shared_source_service,
        )

    async def explain_inference(
        self,
        entity_id: UUID,
        role_type: str,
        scope_filter: Optional[ScopeFilter] = None,
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

        role_evidence = await self.inference_service.list_role_evidence(
            entity_id, scope_filter
        )
        contributing_evidence = role_evidence.get(role_type, [])

        # 4. Build natural language summary
        summary = self._generate_summary(
            role_inference, contributing_evidence, role_type
        )

        # 5. Build confidence breakdown
        confidence_factors = await self._build_confidence_breakdown(
            role_inference, contributing_evidence
        )

        # 6. Identify contradictions
        contradictions = build_contradiction_detail(
            contributing_evidence, role_inference.disagreement
        )

        # 7. Build source chain
        source_chain = await self._build_source_chain(
            contributing_evidence
        )
        contradictions = attach_contradiction_sources(contradictions, source_chain)

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

    def _generate_summary(
        self,
        role_inference: RoleInference,
        contributing_evidence: List[RoleEvidenceRead],
        role_type: str,
    ) -> SummaryData:
        """
        Return structured summary data for the inference.

        The frontend composes the natural-language prose using these keys with
        i18n, avoiding hardcoded English strings in the API response.
        """
        num_sources = self._count_unique_sources(contributing_evidence)
        score = role_inference.score
        confidence = role_inference.confidence
        disagreement = role_inference.disagreement

        # Direction key
        if score is None:
            direction = "none"
        elif score > 0.5:
            direction = "strong_positive"
        elif score > 0.0:
            direction = "weak_positive"
        elif score == 0.0:
            direction = "neutral"
        elif score > -0.5:
            direction = "weak_negative"
        else:
            direction = "strong_negative"

        # Confidence tier key
        if confidence > 0.8:
            confidence_level = "high"
        elif confidence > 0.5:
            confidence_level = "moderate"
        else:
            confidence_level = "low"

        # Disagreement tier key
        if disagreement > 0.5:
            disagreement_level = "significant"
        elif disagreement > 0.2:
            disagreement_level = "some"
        else:
            disagreement_level = "none"

        return SummaryData(
            source_count=num_sources,
            score=score,
            direction=direction,
            confidence_level=confidence_level,
            confidence_pct=round(confidence * 100),
            disagreement_level=disagreement_level,
            role_type=role_type,
        )

    async def _build_confidence_breakdown(
        self,
        role_inference: RoleInference,
        contributing_evidence: List[RoleEvidenceRead],
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
                explanation=(
                    "Total information coverage from "
                    f"{self._count_unique_sources(contributing_evidence)} unique sources"
                ),
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

        # Trust levels (if available) - fetch from source objects
        trust_levels = []
        seen_source_ids: set[UUID] = set()
        for evidence in contributing_evidence:
            source_id = evidence.relation.source_id
            if source_id in seen_source_ids:
                continue
            seen_source_ids.add(source_id)

            source = await self.source_service.get(source_id)
            if source and source.trust_level is not None:
                trust_levels.append(source.trust_level)

        if trust_levels:
            avg_trust = sum(trust_levels) / len(trust_levels)
            factors.append(
                ConfidenceFactor(
                    factor="Average Source Trust",
                    value=avg_trust,
                    explanation=f"Average trust level across {len(trust_levels)} unique rated sources",
                )
            )

        return factors

    def _count_unique_sources(
        self,
        contributing_evidence: List[RoleEvidenceRead],
    ) -> int:
        return len({evidence.relation.source_id for evidence in contributing_evidence})

    async def _build_source_chain(
        self,
        contributing_evidence: List[RoleEvidenceRead],
    ) -> List[SourceContribution]:
        """
        Build complete source chain with provenance.

        For each contributing relation:
        - Source metadata (title, authors, year, URL, trust)
        - Relation details (kind, direction, confidence, scope)
        - Role contribution weight
        - Contribution percentage

        Works with both:
        - Regular source relations (use confidence + direction)
        - Computed relations (use role.weight if available)

        Returns:
            List of SourceContribution objects sorted by contribution percentage
        """
        source_chain = []
        total_weight = sum(evidence.contribution_weight for evidence in contributing_evidence)

        # Build source contributions
        for evidence in contributing_evidence:
            relation = evidence.relation
            # Fetch source metadata from database
            source = await self.source_service.get(relation.source_id)
            if not source:
                continue

            # Calculate contribution percentage
            contribution_pct = (
                (evidence.contribution_weight / total_weight * 100) if total_weight > 0 else 0
            )

            source_chain.append(
                SourceContribution(
                    # Source metadata
                    source_id=source.id,
                    source_title=source.title or "Unknown",
                    source_authors=source.authors or [],
                    source_year=source.year,
                    source_kind=source.kind or "unknown",
                    source_trust=source.trust_level,
                    source_url=source.url or "#",
                    # Relation metadata
                    relation_id=relation.id,
                    relation_kind=relation.kind or "unknown",
                    relation_direction=evidence.contribution_direction,
                    relation_confidence=relation.confidence or 1.0,
                    relation_scope=relation.scope,
                    relation_notes=relation.notes,
                    # Contribution analysis
                    role_weight=evidence.role_weight,
                    contribution_percentage=contribution_pct,
                )
            )

        # Sort by contribution percentage (descending)
        source_chain.sort(key=lambda x: x.contribution_percentage, reverse=True)

        return source_chain
