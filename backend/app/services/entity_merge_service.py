"""
Entity Merge Service - Detect and merge duplicate entities.

Provides:
- Automatic duplicate detection (similar slugs, terms)
- Entity merging (move relations, add terms, soft delete)
- Entity terms management for aliases
"""
import logging
import re
from collections import defaultdict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, update, func
from difflib import SequenceMatcher

from app.models.entity import Entity
from app.models.entity_merge_record import EntityMergeRecord
from app.models.entity_revision import EntityRevision
from app.models.entity_term import EntityTerm
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.repositories.computed_relation_repo import ComputedRelationRepository
from app.schemas.entity_merge import (
    AutoMergeAction,
    EntityMergeCandidate,
    EntityMergeCandidateEntity,
    EntityMergeResult,
)


logger = logging.getLogger(__name__)


class EntityMergeService:
    """Service for detecting and merging duplicate entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_potential_duplicates(
        self,
        similarity_threshold: float = 0.8
    ) -> list[tuple[UUID, UUID, float]]:
        """
        Find pairs of entities that are likely duplicates.

        Uses:
        - Slug similarity (Levenshtein distance)
        - Term matching (check if one entity's slug matches another's terms)

        Returns:
            List of (entity_id_1, entity_id_2, similarity_score)
        """
        # Get all current entities
        stmt = select(Entity, EntityRevision).join(
            EntityRevision, Entity.id == EntityRevision.entity_id
        ).where(EntityRevision.is_current == True)

        result = await self.db.execute(stmt)
        entities = [(entity, revision) for entity, revision in result]

        duplicates = []

        # Compare each pair
        for i, (entity1, rev1) in enumerate(entities):
            for entity2, rev2 in entities[i + 1:]:
                # Calculate slug similarity
                similarity = SequenceMatcher(
                    None,
                    rev1.slug.lower(),
                    rev2.slug.lower()
                ).ratio()

                if similarity >= similarity_threshold:
                    duplicates.append((entity1.id, entity2.id, similarity))
                    logger.info(
                        f"Potential duplicate: {rev1.slug} vs {rev2.slug} "
                        f"(similarity: {similarity:.2f})"
                    )

        # Also check if one entity's slug matches another's terms
        stmt = select(EntityTerm)
        result = await self.db.execute(stmt)
        terms = result.scalars().all()

        for entity, revision in entities:
            for term in terms:
                if term.entity_id != entity.id:
                    # Check if this entity's slug matches another entity's term
                    if revision.slug.lower() == term.term.lower():
                        duplicates.append((entity.id, term.entity_id, 1.0))
                        logger.info(
                            f"Slug matches term: {revision.slug} = term of entity {term.entity_id}"
                        )

        return duplicates

    async def merge_entities(
        self,
        source_entity_id: UUID,
        target_entity_id: UUID,
        preserve_source_slug_as_term: bool = True,
        merged_by_user_id: UUID | None = None,
    ) -> EntityMergeResult:
        """
        Merge source entity into target entity.

        Process:
        1. Move all relation_role_revisions from source to target
        2. Add source entity's slug as term to target entity
        3. Mark source entity as merged (soft delete)

        Args:
            source_entity_id: Entity to merge (will be disabled)
            target_entity_id: Entity to merge into (will receive relations)
            preserve_source_slug_as_term: Add source slug to target's terms

        Returns:
            Statistics about the merge
        """
        # Guard: self-merge is invalid (DF-MRG-M1)
        if source_entity_id == target_entity_id:
            raise ValueError("Cannot merge entity with itself: source and target must be different entities")

        # Guard: check for circular merge — reject if either entity already appears
        # as a source in an existing merge record involving the other (DF-MRG-C1)
        circular_stmt = select(EntityMergeRecord).where(
            EntityMergeRecord.source_entity_id.in_([source_entity_id, target_entity_id]),
            EntityMergeRecord.target_entity_id.in_([source_entity_id, target_entity_id]),
        )
        circular_result = await self.db.execute(circular_stmt)
        if circular_result.scalar_one_or_none():
            raise ValueError(
                "Circular merge detected: one of these entities has already been merged into the other"
            )

        # Get source and target entities
        stmt = select(Entity, EntityRevision).join(
            EntityRevision, Entity.id == EntityRevision.entity_id
        ).where(
            EntityRevision.is_current == True,
            Entity.id.in_([source_entity_id, target_entity_id])
        )

        result = await self.db.execute(stmt)
        entities_map = {entity.id: (entity, revision) for entity, revision in result}

        if source_entity_id not in entities_map:
            raise ValueError(f"Source entity {source_entity_id} not found")
        if target_entity_id not in entities_map:
            raise ValueError(f"Target entity {target_entity_id} not found")

        _, source_revision = entities_map[source_entity_id]
        _, target_revision = entities_map[target_entity_id]

        logger.info(
            f"Merging entity '{source_revision.slug}' into '{target_revision.slug}'"
        )

        try:
            # Invalidate inference cache for both entities before moving roles (DF-MRG-M2).
            # Must happen before the UPDATE so the join-based lookup still finds the right rows.
            cache_repo = ComputedRelationRepository(self.db)
            await cache_repo.delete_by_entity_id(source_entity_id)
            await cache_repo.delete_by_entity_id(target_entity_id)

            # Count current-revision roles before merge (for result reporting)
            stmt = select(func.count()).select_from(RelationRoleRevision).where(
                RelationRoleRevision.entity_id == source_entity_id
            ).join(
                RelationRevision,
                RelationRoleRevision.relation_revision_id == RelationRevision.id,
            ).where(RelationRevision.is_current == True)  # noqa: E712
            result = await self.db.execute(stmt)
            relations_count = result.scalar()

            # Deduplicate participant collisions before rewriting remaining rows.
            # If the target entity already occupies the same role in a current revision,
            # keep the canonical target row and delete the source duplicate.
            duplicate_rows_stmt = (
                select(
                    RelationRoleRevision.id,
                    RelationRoleRevision.relation_revision_id,
                    RelationRoleRevision.role_type,
                )
                .join(
                    RelationRevision,
                    RelationRoleRevision.relation_revision_id == RelationRevision.id,
                )
                .where(
                    RelationRevision.is_current == True,  # noqa: E712
                    RelationRoleRevision.entity_id == source_entity_id,
                )
            )
            duplicate_rows = (await self.db.execute(duplicate_rows_stmt)).all()

            duplicate_source_role_ids: list[UUID] = []
            for role_row_id, relation_revision_id, role_type in duplicate_rows:
                target_role_stmt = select(RelationRoleRevision.id).where(
                    RelationRoleRevision.relation_revision_id == relation_revision_id,
                    RelationRoleRevision.entity_id == target_entity_id,
                    RelationRoleRevision.role_type == role_type,
                )
                target_role_id = (await self.db.execute(target_role_stmt)).scalar_one_or_none()
                if target_role_id is not None:
                    duplicate_source_role_ids.append(role_row_id)

            if duplicate_source_role_ids:
                await self.db.execute(
                    delete(RelationRoleRevision).where(
                        RelationRoleRevision.id.in_(duplicate_source_role_ids)
                    )
                )

            # Move roles from source to target — only in current revisions.
            # Historical revisions are immutable snapshots and must not be changed.
            current_revision_ids_stmt = (
                select(RelationRevision.id).where(RelationRevision.is_current == True)  # noqa: E712
            )
            await self.db.execute(
                update(RelationRoleRevision)
                .where(
                    RelationRoleRevision.entity_id == source_entity_id,
                    RelationRoleRevision.relation_revision_id.in_(current_revision_ids_stmt),
                )
                .values(entity_id=target_entity_id)
            )

            # Add source slug as term to target entity
            if preserve_source_slug_as_term:
                # Check if term already exists
                stmt = select(EntityTerm).where(
                    EntityTerm.entity_id == target_entity_id,
                    EntityTerm.term == source_revision.slug
                )
                result = await self.db.execute(stmt)
                existing_term = result.scalar_one_or_none()

                if not existing_term:
                    term = EntityTerm(
                        entity_id=target_entity_id,
                        term=source_revision.slug,
                        language="en",
                        display_order=None
                    )
                    self.db.add(term)

                    logger.info(f"Added term '{source_revision.slug}' to entity '{target_revision.slug}'")

            merge_record = EntityMergeRecord(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                merged_by_user_id=merged_by_user_id,
                source_slug=source_revision.slug,
                target_slug=target_revision.slug,
            )
            self.db.add(merge_record)

            # Mark source entity as merged.
            # Set is_merged=True on the Entity row so list/search/export queries
            # can filter it out efficiently. Also deactivate all revisions so
            # canonical-predicate joins find no current revision. (NEW-MRG-M1)
            await self.db.execute(
                update(Entity)
                .where(Entity.id == source_entity_id)
                .values(is_merged=True)
            )
            await self.db.execute(
                update(EntityRevision)
                .where(EntityRevision.entity_id == source_entity_id)
                .values(is_current=False)
            )

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

        logger.info(
            f"Merge complete: {relations_count} relations moved, "
            f"source entity marked as merged"
        )

        return EntityMergeResult(
            source_slug=source_revision.slug,
            target_slug=target_revision.slug,
            relations_moved=relations_count or 0,
            term_added=preserve_source_slug_as_term,
            merge_recorded=True,
        )

    async def auto_merge_obvious_duplicates(
        self,
        dry_run: bool = True
    ) -> list[AutoMergeAction]:
        """
        Automatically merge obvious duplicates.

        Obvious duplicates:
        - Same slug with suffix (fibromyalgia vs fibromyalgia-syndrome)
        - >90% similarity
        - One is subset of the other

        Args:
            dry_run: If True, only report duplicates without merging

        Returns:
            List of merge actions (performed or suggested)
        """
        duplicates = await self.find_potential_duplicates(similarity_threshold=0.9)
        merge_actions: list[AutoMergeAction] = []

        for source_id, target_id, similarity in duplicates:
            # Get slugs
            stmt = select(EntityRevision).where(
                EntityRevision.entity_id.in_([source_id, target_id]),
                EntityRevision.is_current == True
            )
            result = await self.db.execute(stmt)
            revisions = {rev.entity_id: rev for rev in result.scalars()}

            source_rev = revisions.get(source_id)
            target_rev = revisions.get(target_id)

            if not source_rev or not target_rev:
                continue

            # Determine which to keep (prefer shorter, simpler slug)
            if len(source_rev.slug) > len(target_rev.slug):
                # Keep target (shorter slug)
                action = AutoMergeAction(
                    source_slug=source_rev.slug,
                    target_slug=target_rev.slug,
                    similarity=similarity,
                    action="merge",
                )
            else:
                # Keep source (shorter slug)
                action = AutoMergeAction(
                    source_slug=target_rev.slug,
                    target_slug=source_rev.slug,
                    similarity=similarity,
                    action="merge",
                )

            if not dry_run:
                # Perform merge
                if len(source_rev.slug) > len(target_rev.slug):
                    result = await self.merge_entities(source_id, target_id)
                else:
                    result = await self.merge_entities(target_id, source_id)

                action.result = result

            merge_actions.append(action)

        logger.info(
            f"Auto-merge: {len(merge_actions)} duplicate pairs found"
            + (" (dry run)" if dry_run else " (merged)")
        )

        return merge_actions

    async def list_merge_candidates(
        self,
        similarity_threshold: float = 0.86,
        limit: int = 50,
    ) -> list[EntityMergeCandidate]:
        """
        Return deterministic entity-merge candidates for admin review.

        This is intentionally a dry-run read model. It proposes likely duplicate
        nodes, but never mutates graph state or treats the suggestion as authoritative.
        """
        rows = await self.db.execute(
            select(Entity, EntityRevision)
            .join(EntityRevision, Entity.id == EntityRevision.entity_id)
            .where(
                EntityRevision.is_current == True,  # noqa: E712
                Entity.is_merged == False,  # noqa: E712
                Entity.is_rejected == False,  # noqa: E712
            )
        )
        entities = [(entity, revision) for entity, revision in rows]
        if len(entities) < 2:
            return []

        entity_ids = {entity.id for entity, _ in entities}
        terms_by_entity = await self._load_terms_by_entity(entity_ids)
        neighborhoods, source_sets = await self._load_relation_context_by_entity(entity_ids)

        candidates: list[EntityMergeCandidate] = []
        for i, (first_entity, first_revision) in enumerate(entities):
            for second_entity, second_revision in entities[i + 1:]:
                score, reason, factors = self._score_merge_candidate(
                    first_revision,
                    second_revision,
                    terms_by_entity.get(first_entity.id, set()),
                    terms_by_entity.get(second_entity.id, set()),
                    neighborhoods.get(first_entity.id, set()),
                    neighborhoods.get(second_entity.id, set()),
                    source_sets.get(first_entity.id, set()),
                    source_sets.get(second_entity.id, set()),
                )
                if score < similarity_threshold:
                    continue

                if len(first_revision.slug) > len(second_revision.slug):
                    source_id = first_entity.id
                    source_revision = first_revision
                    target_id = second_entity.id
                    target_revision = second_revision
                else:
                    source_id = second_entity.id
                    source_revision = second_revision
                    target_id = first_entity.id
                    target_revision = first_revision

                candidates.append(
                    EntityMergeCandidate(
                        source=EntityMergeCandidateEntity(
                            id=source_id,
                            slug=source_revision.slug,
                            summary=source_revision.summary,
                        ),
                        target=EntityMergeCandidateEntity(
                            id=target_id,
                            slug=target_revision.slug,
                            summary=target_revision.summary,
                        ),
                        similarity=round(score, 4),
                        reason=reason,
                        score_factors={
                            **factors,
                            "source_slug_length": len(source_revision.slug),
                            "target_slug_length": len(target_revision.slug),
                        },
                    )
                )

        candidates.sort(key=lambda candidate: candidate.similarity, reverse=True)

        return candidates[:limit]

    async def _load_terms_by_entity(self, entity_ids: set[UUID]) -> dict[UUID, set[str]]:
        if not entity_ids:
            return {}

        result = await self.db.execute(
            select(EntityTerm).where(EntityTerm.entity_id.in_(entity_ids))
        )
        terms_by_entity: dict[UUID, set[str]] = defaultdict(set)
        for term in result.scalars():
            normalized = self._normalize_match_text(term.term)
            if normalized:
                terms_by_entity[term.entity_id].add(normalized)
        return terms_by_entity

    async def _load_relation_context_by_entity(
        self,
        entity_ids: set[UUID],
    ) -> tuple[dict[UUID, set[UUID]], dict[UUID, set[UUID]]]:
        if not entity_ids:
            return {}, {}

        result = await self.db.execute(
            select(
                Relation.id,
                Relation.source_id,
                RelationRoleRevision.entity_id,
            )
            .join(RelationRevision, Relation.id == RelationRevision.relation_id)
            .join(
                RelationRoleRevision,
                RelationRevision.id == RelationRoleRevision.relation_revision_id,
            )
            .where(
                RelationRevision.is_current == True,  # noqa: E712
                RelationRevision.status == "confirmed",
                Relation.is_rejected == False,  # noqa: E712
            )
        )

        relation_entities: dict[UUID, set[UUID]] = defaultdict(set)
        relation_sources: dict[UUID, UUID] = {}
        for relation_id, source_id, entity_id in result:
            relation_entities[relation_id].add(entity_id)
            relation_sources[relation_id] = source_id

        neighborhoods: dict[UUID, set[UUID]] = defaultdict(set)
        source_sets: dict[UUID, set[UUID]] = defaultdict(set)
        for relation_id, participants in relation_entities.items():
            source_id = relation_sources[relation_id]
            for entity_id in participants & entity_ids:
                neighborhoods[entity_id].update(participants - {entity_id})
                source_sets[entity_id].add(source_id)

        return neighborhoods, source_sets

    def _score_merge_candidate(
        self,
        first_revision: EntityRevision,
        second_revision: EntityRevision,
        first_terms: set[str],
        second_terms: set[str],
        first_neighbors: set[UUID],
        second_neighbors: set[UUID],
        first_sources: set[UUID],
        second_sources: set[UUID],
    ) -> tuple[float, str, dict[str, float | str | bool]]:
        first_slug = self._normalize_match_text(first_revision.slug)
        second_slug = self._normalize_match_text(second_revision.slug)
        slug_similarity = SequenceMatcher(None, first_slug, second_slug).ratio()
        contains_slug = first_slug in second_slug or second_slug in first_slug

        first_names = {first_slug, *first_terms}
        second_names = {second_slug, *second_terms}
        term_similarity = max(
            (
                SequenceMatcher(None, first_name, second_name).ratio()
                for first_name in first_names
                for second_name in second_names
            ),
            default=0.0,
        )
        exact_term_overlap = bool(first_names & second_names)

        summary_overlap = self._summary_token_overlap(
            first_revision.summary,
            second_revision.summary,
        )
        shared_neighbor_count = len(first_neighbors & second_neighbors)
        shared_source_count = len(first_sources & second_sources)
        shared_neighbor_score = min(shared_neighbor_count / 3, 1.0)
        shared_source_score = min(shared_source_count / 3, 1.0)
        same_category = (
            first_revision.ui_category_id is not None
            and first_revision.ui_category_id == second_revision.ui_category_id
        )

        score = max(slug_similarity, term_similarity)
        if contains_slug:
            score += 0.03
        if same_category:
            score += 0.03
        score += summary_overlap * 0.08
        score += shared_neighbor_score * 0.08
        score += shared_source_score * 0.06
        score = min(score, 1.0)

        reason = "Very similar entity slugs"
        if exact_term_overlap or term_similarity >= 0.99:
            reason = "Exact or alias-level term match"
        elif contains_slug:
            reason = "One slug contains the other"
        elif shared_neighbor_count and shared_source_count:
            reason = "Similar names with shared relation neighborhoods and sources"
        elif summary_overlap >= 0.5:
            reason = "Similar names with overlapping summaries"

        return (
            score,
            reason,
            {
                "slug_similarity": round(slug_similarity, 4),
                "term_similarity": round(term_similarity, 4),
                "contains_slug": contains_slug,
                "same_ui_category": same_category,
                "summary_token_overlap": round(summary_overlap, 4),
                "shared_relation_neighbors": shared_neighbor_count,
                "shared_sources": shared_source_count,
                "both_have_summary": bool(first_revision.summary and second_revision.summary),
            },
        )

    def _summary_token_overlap(
        self,
        first_summary: dict[str, str] | None,
        second_summary: dict[str, str] | None,
    ) -> float:
        first_tokens = self._summary_tokens(first_summary)
        second_tokens = self._summary_tokens(second_summary)
        if not first_tokens or not second_tokens:
            return 0.0
        return len(first_tokens & second_tokens) / len(first_tokens | second_tokens)

    def _summary_tokens(self, summary: dict[str, str] | None) -> set[str]:
        if not summary:
            return set()
        text = " ".join(value for value in summary.values() if value)
        return {
            token
            for token in re.findall(r"[a-z0-9]+", text.lower())
            if len(token) > 2
        }

    def _normalize_match_text(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
