import hashlib
import json
from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.llm.base import LLMError, LLMProvider
from app.mappers.relation_mapper import relation_to_read
from app.models.graph_cleaning_decision import GraphCleaningDecision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.source_revision import SourceRevision
from app.repositories.computed_relation_repo import ComputedRelationRepository
from app.schemas.relation import RelationWrite, RoleRevisionWrite
from app.schemas.graph_cleaning import (
    DuplicateRelationCandidate,
    DuplicateRelationItem,
    DuplicateRelationApplyRequest,
    GraphCleaningActionResult,
    GraphCleaningAnalysis,
    GraphCleaningCritiqueItem,
    GraphCleaningCritiqueRequest,
    GraphCleaningCritiqueResponse,
    GraphCleaningDecisionRead,
    GraphCleaningDecisionWrite,
    GraphCleaningRelationRole,
    RoleCorrectionRequest,
    RoleConsistencyCandidate,
    RoleUsageCount,
)
from app.services.relation_service import RelationService
from app.services.inference.read_models import resolve_entity_slugs
from app.services.query_predicates import canonical_relation_predicate
from app.utils.errors import AppException, ErrorCode, RelationNotFoundException, ValidationException
from app.utils.revision_helpers import get_current_revision


class GraphCleaningService:
    """Read-only graph-cleaning analysis service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze(self, limit: int = 50) -> GraphCleaningAnalysis:
        """Return the current read-only graph-cleaning analysis."""
        duplicate_relations = await self.list_duplicate_relation_candidates(limit=limit)
        role_consistency = await self.list_role_consistency_candidates(limit=limit)
        return GraphCleaningAnalysis(
            duplicate_relations=duplicate_relations,
            role_consistency=role_consistency,
        )

    async def list_decisions(self) -> list[GraphCleaningDecisionRead]:
        rows = (
            await self.db.execute(
                select(GraphCleaningDecision).order_by(GraphCleaningDecision.updated_at.desc())
            )
        ).scalars().all()
        return [self._decision_to_read(row) for row in rows]

    async def upsert_decision(
        self,
        payload: GraphCleaningDecisionWrite,
        reviewer_id: UUID | None,
    ) -> GraphCleaningDecisionRead:
        existing = (
            await self.db.execute(
                select(GraphCleaningDecision).where(
                    GraphCleaningDecision.candidate_type == payload.candidate_type,
                    GraphCleaningDecision.candidate_fingerprint == payload.candidate_fingerprint,
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            decision = GraphCleaningDecision(
                candidate_type=payload.candidate_type,
                candidate_fingerprint=payload.candidate_fingerprint,
                status=payload.status,
                notes=payload.notes,
                decision_payload=payload.decision_payload,
                reviewed_by_user_id=reviewer_id,
            )
            self.db.add(decision)
        else:
            decision = existing
            decision.status = payload.status
            decision.notes = payload.notes
            decision.decision_payload = payload.decision_payload
            decision.reviewed_by_user_id = reviewer_id

        await self.db.commit()
        await self.db.refresh(decision)
        return self._decision_to_read(decision)

    async def critique_candidates(
        self,
        payload: GraphCleaningCritiqueRequest,
        llm_provider: LLMProvider,
    ) -> GraphCleaningCritiqueResponse:
        """Ask an LLM for non-authoritative critical analysis of candidates."""
        candidates = [
            self._summarize_critique_candidate(candidate)
            for candidate in payload.candidates[:10]
        ]
        system_prompt = (
            "You critique graph-cleaning candidates for an evidence knowledge graph. "
            "You are advisory only. Never state that a merge or cleanup is certain. "
            "Return JSON with an items array. Each item must include "
            "candidate_fingerprint, recommendation (recommend, reject, or "
            "needs_human_review), rationale, risks, and evidence_gaps. "
            "Keep each rationale, risk, and evidence gap under 20 words."
        )
        try:
            response = await llm_provider.generate_json(
                prompt=json.dumps({"candidates": candidates}, default=str),
                system_prompt=system_prompt,
                temperature=0,
                max_tokens=4000,
            )
        except LLMError as exc:
            raise AppException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                error_code=ErrorCode.LLM_API_ERROR,
                message="LLM critique failed",
                details=str(exc),
                context={"finish_reason": exc.finish_reason} if exc.finish_reason else None,
            ) from exc
        raw_items = response.get("items", [])
        items = [GraphCleaningCritiqueItem.model_validate(item) for item in raw_items]
        return GraphCleaningCritiqueResponse(
            model=llm_provider.get_model_name(),
            items=items,
        )

    def _summarize_critique_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        """Keep LLM critique payloads compact enough to avoid truncation."""
        candidate_type = candidate.get("candidate_type")
        summary: dict[str, Any] = {
            "candidate_fingerprint": candidate.get("candidate_fingerprint"),
            "candidate_type": candidate_type,
            "reason": candidate.get("reason"),
        }
        if candidate_type == "entity_merge":
            summary.update(
                {
                    "source_slug": candidate.get("source_slug"),
                    "target_slug": candidate.get("target_slug"),
                    "similarity": candidate.get("similarity"),
                }
            )
        elif candidate_type == "duplicate_relation":
            relations = candidate.get("relations") or []
            first_relation = relations[0] if relations else {}
            summary.update(
                {
                    "relation_count": candidate.get("relation_count"),
                    "source_title": candidate.get("source_title"),
                    "relation_kind": first_relation.get("kind"),
                    "direction": first_relation.get("direction"),
                    "roles": [
                        {
                            "role_type": role.get("role_type"),
                            "entity_slug": role.get("entity_slug"),
                        }
                        for role in (first_relation.get("roles") or [])
                    ],
                }
            )
        elif candidate_type == "role_consistency":
            summary.update(
                {
                    "entity_slug": candidate.get("entity_slug"),
                    "relation_kind": candidate.get("relation_kind"),
                    "role_usages": [
                        {
                            "role_type": usage.get("role_type"),
                            "count": usage.get("count"),
                        }
                        for usage in (candidate.get("usages") or [])
                    ],
                }
            )
        return summary

    async def apply_duplicate_relation_review(
        self,
        payload: DuplicateRelationApplyRequest,
        reviewer_id: UUID | None,
    ) -> GraphCleaningActionResult:
        """Mark reviewed duplicate relations as rejected/duplicate without deleting evidence."""
        relation_ids = set(payload.duplicate_relation_ids)
        rows = (
            await self.db.execute(
                select(Relation, RelationRevision)
                .join(RelationRevision, Relation.id == RelationRevision.relation_id)
                .where(
                    Relation.id.in_(relation_ids),
                    RelationRevision.is_current == True,  # noqa: E712
                )
                .options(selectinload(RelationRevision.roles))
            )
        ).all()
        found_ids = {relation.id for relation, _ in rows}
        missing_ids = relation_ids - found_ids
        if missing_ids:
            raise RelationNotFoundException(str(next(iter(missing_ids))))

        affected_entity_ids = {
            role.entity_id
            for _, revision in rows
            for role in revision.roles
        }
        for relation, revision in rows:
            revision.notes = {
                **(revision.notes or {}),
                "graph_cleaning": (
                    f"Marked duplicate by admin review. Rationale: {payload.rationale}"
                ),
            }
            relation.is_rejected = True

        computed_repo = ComputedRelationRepository(self.db)
        for entity_id in affected_entity_ids:
            await computed_repo.delete_by_entity_id(entity_id)

        result_payload = {
            "action": "mark_duplicate_relations",
            "affected_relation_ids": [str(relation_id) for relation_id in sorted(relation_ids, key=str)],
            "rationale": payload.rationale,
        }
        if payload.candidate_fingerprint:
            await self._mark_decision_applied(
                "duplicate_relation",
                payload.candidate_fingerprint,
                reviewer_id,
                result_payload,
            )

        await self.db.commit()
        return GraphCleaningActionResult(
            action="mark_duplicate_relations",
            affected_relation_ids=sorted(relation_ids, key=str),
            status="applied",
        )

    async def apply_role_correction(
        self,
        relation_id: UUID,
        payload: RoleCorrectionRequest,
        reviewer_id: UUID | None,
    ) -> GraphCleaningActionResult:
        """Create a new relation revision with corrected role labels."""
        relation = (
            await self.db.execute(select(Relation).where(Relation.id == relation_id))
        ).scalar_one_or_none()
        if relation is None:
            raise RelationNotFoundException(str(relation_id))
        current_revision = await get_current_revision(
            db=self.db,
            revision_class=RelationRevision,
            parent_id_field="relation_id",
            parent_id=relation_id,
            load_relationships=["roles"],
        )
        if current_revision is None:
            raise RelationNotFoundException(str(relation_id))

        correction_map = {
            (correction.entity_id, correction.from_role_type): correction.to_role_type
            for correction in payload.corrections
        }
        applied = 0
        new_roles: list[RoleRevisionWrite] = []
        for role in current_revision.roles:
            role_type = correction_map.get((role.entity_id, role.role_type), role.role_type)
            if role_type != role.role_type:
                applied += 1
            new_roles.append(
                RoleRevisionWrite(
                    entity_id=role.entity_id,
                    role_type=role_type,
                    weight=role.weight,
                    coverage=role.coverage,
                )
            )
        if applied == 0:
            raise ValidationException(
                message="No matching roles to correct",
                field="corrections",
                details="At least one correction must match an entity and current role.",
            )

        relation_service = RelationService(self.db)
        read = await relation_service.update(
            relation_id,
            RelationWrite(
                source_id=relation.source_id,
                kind=current_revision.kind or "other",
                direction=current_revision.direction,
                confidence=current_revision.confidence,
                scope=current_revision.scope,
                notes={
                    **(current_revision.notes or {}),
                    "graph_cleaning": (
                        f"Role correction by admin review. Rationale: {payload.rationale}"
                    ),
                },
                roles=new_roles,
            ),
            user_id=reviewer_id,
        )

        result_payload = {
            "action": "correct_relation_roles",
            "affected_relation_ids": [str(relation_id)],
            "created_revision_ids": [str(read.updated_at)],
            "rationale": payload.rationale,
        }
        if payload.candidate_fingerprint:
            await self._mark_decision_applied(
                "role_consistency",
                payload.candidate_fingerprint,
                reviewer_id,
                result_payload,
                commit=True,
            )

        current_after = await get_current_revision(
            db=self.db,
            revision_class=RelationRevision,
            parent_id_field="relation_id",
            parent_id=relation_id,
        )
        return GraphCleaningActionResult(
            action="correct_relation_roles",
            affected_relation_ids=[relation_id],
            created_revision_ids=[current_after.id] if current_after else [],
            status="applied",
        )

    async def list_duplicate_relation_candidates(
        self,
        limit: int = 50,
    ) -> list[DuplicateRelationCandidate]:
        """
        Find current confirmed relations from the same source with identical signatures.

        The signature includes relation kind, direction, normalized scope, and the full
        set of role/entity participants. This is intentionally conservative and read-only.
        """
        rows = await self._load_current_relation_rows()
        entity_slug_map = await self._resolve_row_entity_slugs(rows)

        groups: dict[tuple[object, ...], list[tuple[Relation, RelationRevision, str | None]]] = (
            defaultdict(list)
        )
        for relation, revision, source_title in rows:
            roles_key = tuple(
                sorted((role.role_type, str(role.entity_id)) for role in revision.roles)
            )
            key = (
                str(relation.source_id),
                revision.kind,
                revision.direction,
                self._stable_json(revision.scope),
                roles_key,
            )
            groups[key].append((relation, revision, source_title))

        candidates: list[DuplicateRelationCandidate] = []
        for key, grouped_rows in groups.items():
            if len(grouped_rows) < 2:
                continue

            relation, _, source_title = grouped_rows[0]
            candidates.append(
                DuplicateRelationCandidate(
                    fingerprint=self._fingerprint(key),
                    reason=(
                        "Same source, relation type, direction, scope, and role participants"
                    ),
                    relation_count=len(grouped_rows),
                    source_id=relation.source_id,
                    source_title=source_title,
                    relations=[
                        self._build_relation_item(item_relation, item_revision, item_source_title, entity_slug_map)
                        for item_relation, item_revision, item_source_title in grouped_rows
                    ],
                )
            )
            if len(candidates) >= limit:
                break

        return candidates

    async def list_role_consistency_candidates(
        self,
        limit: int = 50,
    ) -> list[RoleConsistencyCandidate]:
        """
        Find entities used with multiple core roles for the same relation kind.

        The result is a warning surface only. Different roles can be legitimate in
        different relation types or source contexts, so this must not auto-correct.
        """
        rows = await self._load_current_relation_rows()
        entity_ids = {
            role.entity_id
            for _, revision, _ in rows
            for role in revision.roles
        }
        entity_slug_map = await resolve_entity_slugs(self.db, entity_ids)

        usage: dict[tuple[UUID, str | None], dict[str, set[UUID]]] = defaultdict(
            lambda: defaultdict(set)
        )
        for relation, revision, _ in rows:
            for role in revision.roles:
                usage[(role.entity_id, revision.kind)][role.role_type].add(relation.id)

        candidates: list[RoleConsistencyCandidate] = []
        for (entity_id, relation_kind), roles_by_type in usage.items():
            if len(roles_by_type) < 2:
                continue
            usages = [
                RoleUsageCount(
                    role_type=role_type,
                    count=len(relation_ids),
                    relation_ids=sorted(relation_ids, key=str),
                )
                for role_type, relation_ids in sorted(roles_by_type.items())
            ]
            candidates.append(
                RoleConsistencyCandidate(
                    entity_id=entity_id,
                    entity_slug=entity_slug_map.get(entity_id),
                    relation_kind=relation_kind,
                    reason="Entity appears with multiple role types for the same relation kind",
                    usages=usages,
                )
            )
            if len(candidates) >= limit:
                break

        return candidates

    async def _load_current_relation_rows(
        self,
    ) -> list[tuple[Relation, RelationRevision, str | None]]:
        stmt = (
            select(Relation, RelationRevision, SourceRevision.title)
            .join(RelationRevision, Relation.id == RelationRevision.relation_id)
            .join(
                SourceRevision,
                (Relation.source_id == SourceRevision.source_id)
                & (SourceRevision.is_current == True)  # noqa: E712
                & (SourceRevision.status == "confirmed"),
            )
            .where(canonical_relation_predicate())
            .options(selectinload(RelationRevision.roles))
            .order_by(RelationRevision.created_at.desc())
        )
        return list((await self.db.execute(stmt)).all())

    async def _resolve_row_entity_slugs(
        self,
        rows: list[tuple[Relation, RelationRevision, str | None]],
    ) -> dict[UUID, str]:
        entity_ids = {
            role.entity_id
            for _, revision, _ in rows
            for role in revision.roles
        }
        return await resolve_entity_slugs(self.db, entity_ids)

    def _build_relation_item(
        self,
        relation: Relation,
        revision: RelationRevision,
        source_title: str | None,
        entity_slug_map: dict[UUID, str],
    ) -> DuplicateRelationItem:
        return DuplicateRelationItem(
            relation_id=relation.id,
            relation_revision_id=revision.id,
            source_id=relation.source_id,
            source_title=source_title,
            kind=revision.kind,
            direction=revision.direction,
            confidence=revision.confidence,
            roles=[
                GraphCleaningRelationRole(
                    entity_id=role.entity_id,
                    entity_slug=entity_slug_map.get(role.entity_id),
                    role_type=role.role_type,
                )
                for role in sorted(revision.roles, key=lambda item: (item.role_type, str(item.entity_id)))
            ],
        )

    def _stable_json(self, value: object) -> str:
        return json.dumps(value or {}, sort_keys=True, separators=(",", ":"))

    def _fingerprint(self, key: tuple[object, ...]) -> str:
        payload = self._stable_json(key)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    async def _mark_decision_applied(
        self,
        candidate_type: str,
        candidate_fingerprint: str,
        reviewer_id: UUID | None,
        action_result: dict,
        *,
        commit: bool = False,
    ) -> None:
        decision = (
            await self.db.execute(
                select(GraphCleaningDecision).where(
                    GraphCleaningDecision.candidate_type == candidate_type,
                    GraphCleaningDecision.candidate_fingerprint == candidate_fingerprint,
                )
            )
        ).scalar_one_or_none()
        if decision is None:
            decision = GraphCleaningDecision(
                candidate_type=candidate_type,
                candidate_fingerprint=candidate_fingerprint,
            )
            self.db.add(decision)
        decision.status = "applied"
        decision.action_result = action_result
        decision.reviewed_by_user_id = reviewer_id
        if commit:
            await self.db.commit()

    def _decision_to_read(self, decision: GraphCleaningDecision) -> GraphCleaningDecisionRead:
        return GraphCleaningDecisionRead(
            id=decision.id,
            candidate_type=decision.candidate_type,
            candidate_fingerprint=decision.candidate_fingerprint,
            status=decision.status,
            notes=decision.notes,
            decision_payload=decision.decision_payload,
            action_result=decision.action_result,
            reviewed_by_user_id=decision.reviewed_by_user_id,
            created_at=decision.created_at,
            updated_at=decision.updated_at,
        )
