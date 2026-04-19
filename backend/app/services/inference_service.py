from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.relation_repo import RelationRepository
from app.repositories.computed_relation_repo import ComputedRelationRepository
from app.schemas.common_types import ScopeFilter
from app.schemas.inference import InferenceDetailRead, InferenceRead
from app.utils.hashing import compute_scope_hash
from app.config import settings
from app.services.source_service import SourceService
from app.services.inference.detail_views import build_inference_detail_read
from app.services.inference.math import (
    aggregate_evidence as aggregate_evidence_metric,
    compute_confidence as compute_confidence_metric,
    compute_disagreement as compute_disagreement_metric,
    compute_relation_score as compute_relation_score_metric,
    compute_role_contribution as compute_role_contribution_metric,
)
from app.services.inference.evidence_views import RoleEvidenceRead, build_role_evidence_views
from app.services.inference.read_models import (
    build_grouped_inference_read,
    cache_computed_inference,
    compute_role_inferences,
    convert_cached_to_inference_read,
    matches_scope,
)


class InferenceService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        source_service: SourceService | None = None,
    ):
        self.db = db
        self.repo = RelationRepository(db)
        self.computed_repo = ComputedRelationRepository(db)
        self.source_service = source_service or SourceService(db)

    async def _list_filtered_relations(
        self,
        entity_id: UUID,
        scope_filter: Optional[ScopeFilter] = None,
    ):
        relations = await self.repo.list_by_entity(entity_id)
        if scope_filter:
            return [relation for relation in relations if matches_scope(relation, scope_filter)]
        return relations

    async def infer_for_entity(
        self,
        entity_id: UUID,
        scope_filter: Optional[ScopeFilter] = None,
        use_cache: bool = True,
    ) -> InferenceRead:
        """
        Compute inferences for an entity, optionally filtered by scope.

        Uses caching to avoid recomputing identical inference queries.

        Args:
            entity_id: Entity to compute inferences for
            scope_filter: Optional dict of scope attributes to filter by.
                         Only relations matching ALL specified scope attributes will be included.
                         Example: {"population": "adults", "condition": "chronic_pain"}
            use_cache: Whether to use cached results (default True)

        Returns:
            - Grouped relations by kind
            - Computed inference scores per role type
        """
        # Check cache first if enabled
        if use_cache:
            scope_hash = compute_scope_hash(entity_id, scope_filter)
            cached = await self.computed_repo.get_by_scope_hash(
                scope_hash,
                settings.INFERENCE_MODEL_VERSION
            )

            if cached:
                # Return cached result - convert ComputedRelation to InferenceRead
                return await convert_cached_to_inference_read(
                    db=self.db,
                    repo=self.repo,
                    entity_id=entity_id,
                    cached_computed=cached,
                    scope_filter=scope_filter,
                )

        relations = await self._list_filtered_relations(entity_id, scope_filter)

        role_inferences = compute_role_inferences(relations, entity_id)
        result = await build_grouped_inference_read(self.db, entity_id, relations, role_inferences)

        # Store in cache if enabled
        if use_cache and role_inferences:
            await cache_computed_inference(
                db=self.db,
                computed_repo=self.computed_repo,
                entity_id=entity_id,
                scope_filter=scope_filter,
                role_inferences=role_inferences,
            )

        return result

    async def list_role_evidence(
        self,
        entity_id: UUID,
        scope_filter: Optional[ScopeFilter] = None,
    ) -> dict[str, list[RoleEvidenceRead]]:
        relations = await self._list_filtered_relations(entity_id, scope_filter)
        return await build_role_evidence_views(self.db, relations)

    async def get_detail_for_entity(
        self,
        entity_id: UUID,
        scope_filter: Optional[ScopeFilter] = None,
        use_cache: bool = True,
    ) -> InferenceDetailRead:
        inference = await self.infer_for_entity(
            entity_id,
            scope_filter=scope_filter,
            use_cache=use_cache,
        )
        return await build_inference_detail_read(
            inference=inference,
            source_service=self.source_service,
        )

    def _compute_role_inferences(
        self,
        relations,
        current_entity_id: UUID | None = None,
    ) -> list:
        return compute_role_inferences(relations, current_entity_id)

    # ============================================================
    # Inference Engine - Mathematical Model Implementation
    # Based on COMPUTED_RELATIONS.md
    # ============================================================

    def compute_relation_score(self, polarity: int, intensity: float) -> float:
        """
        Compute relation-level score.

        Formula: x(c) = p(c) × i(c)

        Args:
            polarity: -1 (negative), 0 (neutral), +1 (positive)
            intensity: strength in (0, 1]

        Returns:
            Score in [-1, 1]
        """
        return compute_relation_score_metric(polarity, intensity)

    def compute_role_contribution(self, relation_scores: list[float]) -> Optional[float]:
        """
        Compute role contribution within a relation.

        Formula: x(h, r) = sum(x(c)) / sum(|x(c)|)

        Args:
            relation_scores: List of signed relation scores for this role

        Returns:
            Contribution in [-1, 1], or None if no relation scores
        """
        return compute_role_contribution_metric(relation_scores)

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
        return aggregate_evidence_metric(relations_data, role)

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
        return compute_confidence_metric(coverage, lambda_param)

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
        return compute_disagreement_metric(relations_data, role)

    def _matches_scope(self, relation, scope_filter: ScopeFilter) -> bool:
        """
        Check if a relation matches the given scope filter.

        Args:
            relation: Relation model with revisions
            scope_filter: Dict of scope attributes to match (AND logic)

        Returns:
            True if relation's scope contains all filter attributes with matching values

        Matching logic:
            - If relation has no scope (None), it does NOT match any filter
            - All filter attributes must exist in relation scope
            - All filter values must match exactly
            - Extra attributes in relation scope are ignored (subset matching)

        Examples:
            filter: {"population": "adults"}
            scope: {"population": "adults", "condition": "chronic"} → True
            scope: {"population": "children"} → False
            scope: None → False

            filter: {"population": "adults", "condition": "chronic"}
            scope: {"population": "adults", "condition": "chronic", "dosage": "high"} → True
            scope: {"population": "adults"} → False (missing condition)
        """
        return matches_scope(relation, scope_filter)

    async def _convert_cached_to_inference_read(
        self,
        entity_id: UUID,
        cached_computed: "ComputedRelation",
        scope_filter: Optional[ScopeFilter],
    ) -> InferenceRead:
        """
        Convert a cached ComputedRelation back to InferenceRead format.

        Args:
            entity_id: Entity the inference is for
            cached_computed: Cached ComputedRelation from database
            scope_filter: Scope filter that was used

        Returns:
            InferenceRead with cached role inferences and fresh relation grouping
        """
        return await convert_cached_to_inference_read(
            db=self.db,
            repo=self.repo,
            entity_id=entity_id,
            cached_computed=cached_computed,
            scope_filter=scope_filter,
        )

    async def _cache_computed_inference(
        self,
        entity_id: UUID,
        scope_filter: Optional[ScopeFilter],
        role_inferences: list,
    ) -> None:
        """
        Store computed inference in cache as a computed relation.

        Creates a new Relation with system source and ComputedRelation metadata.

        Args:
            entity_id: Entity the inference is for
            scope_filter: Scope filter used for inference
            role_inferences: Computed role inferences to cache
        """
        await cache_computed_inference(
            db=self.db,
            computed_repo=self.computed_repo,
            entity_id=entity_id,
            scope_filter=scope_filter,
            role_inferences=role_inferences,
        )
