from collections import defaultdict
from uuid import UUID, uuid4
from typing import Optional
import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.repositories.relation_repo import RelationRepository
from app.repositories.computed_relation_repo import ComputedRelationRepository
from app.mappers.relation_mapper import relation_to_read
from app.schemas.inference import InferenceRead
from app.utils.hashing import compute_scope_hash
from app.config import settings
from app.models.entity_revision import EntityRevision


class InferenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RelationRepository(db)
        self.computed_repo = ComputedRelationRepository(db)

    async def _resolve_entity_slugs(self, entity_ids: set[UUID]) -> dict[UUID, str]:
        """
        Resolve entity IDs to their current slugs.

        Args:
            entity_ids: Set of entity UUIDs to resolve

        Returns:
            Dict mapping entity_id to slug
        """
        if not entity_ids:
            return {}

        stmt = select(EntityRevision.entity_id, EntityRevision.slug).where(
            EntityRevision.entity_id.in_(entity_ids),
            EntityRevision.is_current == True
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        return {row.entity_id: row.slug for row in rows}

    async def infer_for_entity(
        self,
        entity_id: UUID,
        scope_filter: Optional[dict] = None,
        use_cache: bool = True
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
        from app.schemas.inference import RoleInference

        # Check cache first if enabled
        if use_cache:
            scope_hash = compute_scope_hash(entity_id, scope_filter)
            cached = await self.computed_repo.get_by_scope_hash(
                scope_hash,
                settings.INFERENCE_MODEL_VERSION
            )

            if cached:
                # Return cached result - convert ComputedRelation to InferenceRead
                return await self._convert_cached_to_inference_read(
                    entity_id=entity_id,
                    cached_computed=cached,
                    scope_filter=scope_filter
                )

        relations = await self.repo.list_by_entity(entity_id)

        # Apply scope filtering if specified
        if scope_filter:
            relations = [rel for rel in relations if self._matches_scope(rel, scope_filter)]

        # Collect all entity IDs from roles to resolve slugs
        entity_ids = set()
        for rel in relations:
            current_rev = next((r for r in rel.revisions if r.is_current), None) if rel.revisions else None
            if current_rev and current_rev.roles:
                for role in current_rev.roles:
                    entity_ids.add(role.entity_id)

        # Resolve entity slugs in batch
        entity_slug_map = await self._resolve_entity_slugs(entity_ids)

        # Group relations by kind for display
        grouped = defaultdict(list)
        for rel in relations:
            # Get current revision
            current_rev = next((r for r in rel.revisions if r.is_current), None) if rel.revisions else None
            relation_read = relation_to_read(rel, current_revision=current_rev, entity_slug_map=entity_slug_map)

            # Group by kind (use revision kind if available, else fallback)
            kind = current_rev.kind if current_rev else rel.kind
            if kind:  # Only group if kind is defined
                grouped[kind].append(relation_read)

        # Compute inference scores per role type
        role_inferences = self._compute_role_inferences(relations)

        result = InferenceRead(
            entity_id=entity_id,
            relations_by_kind=dict(grouped),
            role_inferences=role_inferences,
        )

        # Store in cache if enabled
        if use_cache and role_inferences:
            await self._cache_computed_inference(entity_id, scope_filter, role_inferences)

        return result

    def _compute_role_inferences(self, relations) -> list:
        """
        Compute inference scores for all RELATION TYPES (not grammatical roles).

        This calculates aggregated inferences by relation type (treats, causes, etc.)
        NOT by grammatical role (subject/object) which would be meaningless.

        Args:
            relations: List of Relation models with current revisions

        Returns:
            List of RoleInference objects with computed scores (role_type = relation kind)
        """
        from app.schemas.inference import RoleInference

        # Collect all unique RELATION TYPES (not role types!)
        relation_types = set()
        for rel in relations:
            # Get current revision
            if rel.revisions:
                current_rev = next((r for r in rel.revisions if r.is_current), None)
                if current_rev and current_rev.kind:
                    relation_types.add(current_rev.kind)

        # Compute inference for each RELATION TYPE
        inferences = []
        for relation_type in relation_types:
            # Prepare relations data for this relation type
            relations_data = []
            relation_count = 0

            for rel in relations:
                # Get current revision
                if rel.revisions:
                    current_rev = next((r for r in rel.revisions if r.is_current), None)
                    if current_rev and current_rev.kind == relation_type:
                        relation_count += 1
                        # Get relation weight (use confidence from revision if available, default 1.0)
                        relation_weight = current_rev.confidence if current_rev.confidence is not None else 1.0

                        # For relation type aggregation, we treat each relation as positive evidence
                        # The direction field indicates if it's supporting or contradicting
                        contribution = 1.0
                        if current_rev.direction == "contradicts":
                            contribution = -1.0
                        elif current_rev.direction is None:
                            contribution = 1.0  # Neutral/unknown = positive

                        relations_data.append({
                            "weight": relation_weight,
                            "roles": {relation_type: contribution}
                        })

            # Compute aggregated inference
            if relations_data:
                result = self.aggregate_evidence(relations_data, role=relation_type)
                confidence = self.compute_confidence(result["coverage"])
                disagreement = self.compute_disagreement(relations_data, role=relation_type)

                inferences.append(RoleInference(
                    role_type=relation_type,  # This is now relation type, not grammatical role
                    score=result["score"],
                    coverage=float(relation_count),  # Number of relations of this type
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

    def _matches_scope(self, relation, scope_filter: dict) -> bool:
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
        # Get current revision
        if not relation.revisions:
            return False

        current_rev = next((r for r in relation.revisions if r.is_current), None)
        if not current_rev:
            return False

        # Get scope from revision
        relation_scope = current_rev.scope

        # If relation has no scope, it doesn't match any filter
        if relation_scope is None:
            return False

        # Check if all filter attributes match
        for key, value in scope_filter.items():
            if key not in relation_scope:
                return False  # Missing attribute
            if relation_scope[key] != value:
                return False  # Value mismatch

        return True  # All filter attributes match

    async def _convert_cached_to_inference_read(
        self,
        entity_id: UUID,
        cached_computed: "ComputedRelation",
        scope_filter: Optional[dict]
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
        from app.schemas.inference import RoleInference

        # Extract role inferences from cached relation's revision roles
        role_inferences = []

        if cached_computed.relation and cached_computed.relation.revisions:
            current_rev = next(
                (r for r in cached_computed.relation.revisions if r.is_current),
                None
            )

            if current_rev and current_rev.roles:
                for role_rev in current_rev.roles:
                    # Reconstruct RoleInference from cached role revision
                    # Note: We can't recover the exact disagreement value, so we use
                    # uncertainty from ComputedRelation as a proxy
                    role_inferences.append(RoleInference(
                        role_type=role_rev.role_type,
                        score=role_rev.weight,  # weight stores the computed score
                        coverage=role_rev.coverage or 0.0,
                        confidence=self.compute_confidence(role_rev.coverage or 0.0),
                        disagreement=cached_computed.uncertainty,  # Use cached uncertainty
                    ))

        # Still need to fetch and group actual relations for relations_by_kind
        # (Cache only stores computed scores, not the full relation list)
        relations = await self.repo.list_by_entity(entity_id)

        # Apply scope filtering if specified
        if scope_filter:
            relations = [rel for rel in relations if self._matches_scope(rel, scope_filter)]

        # Collect all entity IDs from roles to resolve slugs
        entity_ids = set()
        for rel in relations:
            current_rev = next((r for r in rel.revisions if r.is_current), None) if rel.revisions else None
            if current_rev and current_rev.roles:
                for role in current_rev.roles:
                    entity_ids.add(role.entity_id)

        # Resolve entity slugs in batch
        entity_slug_map = await self._resolve_entity_slugs(entity_ids)

        # Group relations by kind for display
        grouped = defaultdict(list)
        for rel in relations:
            current_rev = next(
                (r for r in rel.revisions if r.is_current),
                None
            ) if rel.revisions else None

            relation_read = relation_to_read(rel, current_revision=current_rev, entity_slug_map=entity_slug_map)

            kind = current_rev.kind if current_rev else rel.kind
            if kind:
                grouped[kind].append(relation_read)

        return InferenceRead(
            entity_id=entity_id,
            relations_by_kind=dict(grouped),
            role_inferences=role_inferences,
        )

    async def _cache_computed_inference(
        self,
        entity_id: UUID,
        scope_filter: Optional[dict],
        role_inferences: list
    ) -> None:
        """
        Store computed inference in cache as a computed relation.

        Creates a new Relation with system source and ComputedRelation metadata.

        Args:
            entity_id: Entity the inference is for
            scope_filter: Scope filter used for inference
            role_inferences: Computed role inferences to cache
        """
        from app.models.relation import Relation
        from app.models.relation_revision import RelationRevision
        from app.models.relation_role_revision import RelationRoleRevision
        from app.models.computed_relation import ComputedRelation

        # Check if system source exists
        # Note: System source is auto-created on startup via app/startup.py
        if not settings.SYSTEM_SOURCE_ID:
            # Cannot cache without system source
            return

        system_source_id = UUID(settings.SYSTEM_SOURCE_ID)

        # Compute scope hash
        scope_hash = compute_scope_hash(entity_id, scope_filter)

        # Check if cache entry already exists for this scope
        existing = await self.computed_repo.get_by_scope_hash(
            scope_hash,
            settings.INFERENCE_MODEL_VERSION
        )

        if existing:
            # Cache already exists, no need to store again
            return

        # Create new Relation for computed inference
        relation = Relation(
            id=uuid4(),
            source_id=system_source_id,
        )
        self.db.add(relation)
        await self.db.flush()

        # Create RelationRevision with computed kind
        revision = RelationRevision(
            relation_id=relation.id,
            kind="computed_inference",
            direction="positive",  # Computed inferences are informational
            confidence=1.0,  # We're confident in our computation
            scope=scope_filter,  # Store the scope this was computed for
            is_current=True,
        )
        self.db.add(revision)
        await self.db.flush()

        # Create role revisions for each computed role inference
        for role_inf in role_inferences:
            role_revision = RelationRoleRevision(
                relation_revision_id=revision.id,
                entity_id=entity_id,
                role_type=role_inf.role_type,
                weight=role_inf.score,
                coverage=role_inf.coverage,
            )
            self.db.add(role_revision)

        await self.db.flush()

        # Compute uncertainty from disagreement
        # Use average disagreement across all role types as uncertainty measure
        avg_disagreement = (
            sum(ri.disagreement for ri in role_inferences) / len(role_inferences)
            if role_inferences else 0.0
        )

        # Create ComputedRelation metadata
        computed_relation = ComputedRelation(
            relation_id=relation.id,
            scope_hash=scope_hash,
            model_version=settings.INFERENCE_MODEL_VERSION,
            uncertainty=avg_disagreement,
        )
        self.db.add(computed_relation)
        await self.db.flush()