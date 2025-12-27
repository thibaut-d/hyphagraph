from collections import defaultdict
from uuid import UUID
from typing import Optional
import math
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.relation_repo import RelationRepository
from app.mappers.relation_mapper import relation_to_read
from app.schemas.inference import InferenceRead


class InferenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RelationRepository(db)

    async def infer_for_entity(self, entity_id: UUID) -> InferenceRead:
        """
        Compute inferences for an entity.

        Returns:
            - Grouped relations by kind
            - Computed inference scores per role type
        """
        from app.schemas.inference import RoleInference

        relations = await self.repo.list_by_entity(entity_id)

        # Group relations by kind for display
        grouped = defaultdict(list)
        for rel in relations:
            # Get current revision
            current_rev = next((r for r in rel.revisions if r.is_current), None) if rel.revisions else None
            relation_read = relation_to_read(rel, current_revision=current_rev)

            # Group by kind (use revision kind if available, else fallback)
            kind = current_rev.kind if current_rev else rel.kind
            if kind:  # Only group if kind is defined
                grouped[kind].append(relation_read)

        # Compute inference scores per role type
        role_inferences = self._compute_role_inferences(relations)

        return InferenceRead(
            entity_id=entity_id,
            relations_by_kind=dict(grouped),
            role_inferences=role_inferences,
        )

    def _compute_role_inferences(self, relations) -> list:
        """
        Compute inference scores for all role types across relations.

        Args:
            relations: List of Relation models with current revisions

        Returns:
            List of RoleInference objects with computed scores
        """
        from app.schemas.inference import RoleInference

        # Collect all unique role types
        role_types = set()
        for rel in relations:
            # Get current revision
            if rel.revisions:
                current_rev = next((r for r in rel.revisions if r.is_current), None)
                if current_rev and current_rev.roles:
                    for role in current_rev.roles:
                        role_types.add(role.role_type)

        # Compute inference for each role type
        inferences = []
        for role_type in role_types:
            # Prepare relations data for this role
            relations_data = []
            for rel in relations:
                # Get relation weight (use confidence if available, default 1.0)
                relation_weight = rel.confidence if rel.confidence is not None else 1.0

                # Get current revision
                if rel.revisions:
                    current_rev = next((r for r in rel.revisions if r.is_current), None)
                    if current_rev and current_rev.roles:
                        # Find role contribution
                        role = next((r for r in current_rev.roles if r.role_type == role_type), None)
                        if role:
                            # Use role weight if available, otherwise assume positive contribution
                            contribution = role.weight if role.weight is not None else 1.0

                            relations_data.append({
                                "weight": relation_weight,
                                "roles": {role_type: contribution}
                            })

            # Compute aggregated inference
            if relations_data:
                result = self.aggregate_evidence(relations_data, role=role_type)
                confidence = self.compute_confidence(result["coverage"])
                disagreement = self.compute_disagreement(relations_data, role=role_type)

                inferences.append(RoleInference(
                    role_type=role_type,
                    score=result["score"],
                    coverage=result["coverage"],
                    confidence=confidence,
                    disagreement=disagreement,
                ))

        return inferences

    # ============================================================
    # Inference Engine - Mathematical Model Implementation
    # Based on COMPUTED_RELATIONS.md
    # ============================================================

    def compute_claim_score(self, polarity: int, intensity: float) -> float:
        """
        Compute claim-level score.

        Formula: x(c) = p(c) × i(c)

        Args:
            polarity: -1 (negative), 0 (neutral), +1 (positive)
            intensity: strength in (0, 1]

        Returns:
            Score in [-1, 1]
        """
        return polarity * intensity

    def compute_role_contribution(self, claims: list[float]) -> Optional[float]:
        """
        Compute role contribution within a relation.

        Formula: x(h, r) = sum(x(c)) / sum(|x(c)|)

        Args:
            claims: List of claim scores for this role

        Returns:
            Contribution in [-1, 1], or None if no claims
        """
        if not claims:
            return None  # Role not exposed

        numerator = sum(claims)
        denominator = sum(abs(c) for c in claims)

        if denominator == 0:
            return 0  # All neutral claims

        contribution = numerator / denominator

        # Clamp to [-1, 1] to handle floating point errors
        return max(-1.0, min(1.0, contribution))

    def aggregate_evidence(
        self,
        relations_data: list[dict],
        role: str
    ) -> dict:
        """
        Aggregate evidence across relations for a specific role.

        Formulas:
        - Evidence: Ev(E, r) = sum(w_h × m(h, r) × x(h, r))
        - Coverage: Cov(E, r) = sum(w_h × m(h, r))
        - Score: s_hat(E, r) = Ev(E, r) / Cov(E, r)

        Args:
            relations_data: List of dicts with 'weight' and 'roles'
            role: Role type to aggregate (e.g., 'effect', 'mechanism')

        Returns:
            Dict with 'score', 'coverage'
        """
        evidence = 0.0
        coverage = 0.0

        for relation in relations_data:
            weight = relation.get("weight", 1.0)
            roles = relation.get("roles", {})

            # Check if role is exposed in this relation (mask)
            if role in roles:
                contribution = roles[role]
                if contribution is not None:
                    evidence += weight * contribution
                    coverage += weight

        # Compute normalized score
        if coverage > 0:
            score = evidence / coverage
        else:
            score = None  # No information

        return {
            "score": score,
            "coverage": coverage,
        }

    def compute_confidence(
        self,
        coverage: float,
        lambda_param: float = 1.0
    ) -> float:
        """
        Compute confidence from coverage.

        Formula: confidence(E, r) = 1 - exp(-λ × Cov(E, r))

        Args:
            coverage: Information coverage
            lambda_param: Saturation speed parameter (default 1.0)

        Returns:
            Confidence in [0, 1)
        """
        if coverage <= 0:
            return 0.0

        return 1 - math.exp(-lambda_param * coverage)

    def compute_disagreement(
        self,
        relations_data: list[dict],
        role: str
    ) -> float:
        """
        Compute disagreement (contradiction) measure.

        Formula:
        Dis(E, r) = 1 - |sum(w_h × m(h, r) × x(h, r))| / sum(w_h × m(h, r) × |x(h, r)|)

        Args:
            relations_data: List of dicts with 'weight' and 'roles'
            role: Role type to check

        Returns:
            Disagreement in [0, 1]:
            - 0 = full agreement
            - 1 = maximal contradiction
        """
        signed_sum = 0.0
        absolute_sum = 0.0

        for relation in relations_data:
            weight = relation.get("weight", 1.0)
            roles = relation.get("roles", {})

            if role in roles:
                contribution = roles[role]
                if contribution is not None:
                    signed_sum += weight * contribution
                    absolute_sum += weight * abs(contribution)

        if absolute_sum == 0:
            return 0.0  # No evidence, no disagreement

        disagreement = 1 - (abs(signed_sum) / absolute_sum)
        return disagreement