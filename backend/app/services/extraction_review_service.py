"""
Service for managing staged extraction review workflow.

Handles:
- Staging extractions for human review
- Approving/rejecting staged extractions
- Materializing approved extractions into knowledge graph
- Auto-commit logic for high-confidence extractions
- Review statistics and querying
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.schemas import ExtractedClaim, ExtractedEntity, ExtractedRelation, ExtractedRole
from app.models.entity import Entity
from app.models.relation import Relation
from app.models.staged_extraction import ExtractionStatus, ExtractionType, StagedExtraction
from app.schemas.staged_extraction import (
    AutoCommitResponse,
    BatchReviewResponse,
    StagedExtractionFilters,
    ReviewStats,
    MaterializationResult,
)
from app.services.extraction_validation_service import ValidationResult, validate_relation_structure
from app.services.extraction_review.auto_commit import check_auto_commit_eligible, run_auto_commit
from app.services.extraction_review.materialization import (
    materialize_claim,
    materialize_entity,
    materialize_relation,
)
from app.services.extraction_review.queries import (
    apply_review_metadata,
    get_stats as get_review_stats,
    list_extractions as list_review_extractions,
    load_staged_extraction,
)
from app.services.extraction_review.staging import create_staged_extraction

logger = logging.getLogger(__name__)


class ExtractionReviewService:
    """
    Service for managing the human-in-the-loop review workflow.

    Key features:
    - Optional staging: high-confidence extractions can auto-commit
    - Batch review operations
    - Materialization of approved extractions
    - Review statistics and reporting
    """

    def __init__(
        self,
        db: AsyncSession,
        auto_commit_enabled: bool = True,
        auto_commit_threshold: float = 0.9,
        require_no_flags_for_auto_commit: bool = True,
    ):
        self.db = db
        self.auto_commit_enabled = auto_commit_enabled
        self.auto_commit_threshold = auto_commit_threshold
        self.require_no_flags_for_auto_commit = require_no_flags_for_auto_commit

    # =========================================================================
    # Staging Operations
    # =========================================================================

    async def stage_extraction(
        self,
        extraction_type: ExtractionType,
        extraction_data: ExtractedEntity | ExtractedRelation | ExtractedClaim,
        source_id: UUID,
        validation_result: ValidationResult,
        llm_model: str | None = None,
        llm_provider: str | None = None,
        auto_materialize: bool = True,
        commit: bool = True,
    ) -> tuple[StagedExtraction, UUID | None]:
        """
        Create extraction metadata and optionally materialize.

        High-confidence extractions get status=auto_verified; others get status=pending.
        Both are materialized immediately by default.
        """
        is_high_confidence = check_auto_commit_eligible(
            validation_result,
            self.auto_commit_enabled,
            self.auto_commit_threshold,
            self.require_no_flags_for_auto_commit,
        )
        threshold = self.auto_commit_threshold if self.auto_commit_enabled else None
        return await create_staged_extraction(
            db=self.db,
            extraction_type=extraction_type,
            extraction_data=extraction_data,
            source_id=source_id,
            validation_result=validation_result,
            llm_model=llm_model,
            llm_provider=llm_provider,
            is_high_confidence=is_high_confidence,
            auto_commit_threshold=threshold,
            auto_materialize=auto_materialize,
            commit=commit,
        )

    async def stage_batch(
        self,
        entities: list[tuple[ExtractedEntity, ValidationResult]],
        relations: list[tuple[ExtractedRelation, ValidationResult]],
        claims: list[tuple[ExtractedClaim, ValidationResult]],
        source_id: UUID,
        llm_model: str | None = None,
        llm_provider: str | None = None,
        auto_materialize: bool = True,
        commit: bool = True,
    ) -> list[StagedExtraction]:
        """Stage a batch of extractions.

        When auto_materialize=False, items are staged for the review queue but not
        yet written to the knowledge graph. The caller is responsible for
        materialising them (e.g. via save_extraction_to_graph) and then calling
        reconcile_staged_extractions to link the resulting IDs back.
        """
        staged_extractions = []

        for entity, validation_result in entities:
            staged, _ = await self.stage_extraction(
                ExtractionType.ENTITY, entity, source_id, validation_result,
                llm_model, llm_provider, auto_materialize=auto_materialize,
                commit=commit,
            )
            staged_extractions.append(staged)

        for relation, validation_result in relations:
            staged, _ = await self.stage_extraction(
                ExtractionType.RELATION, relation, source_id, validation_result,
                llm_model, llm_provider, auto_materialize=auto_materialize,
                commit=commit,
            )
            staged_extractions.append(staged)

        for claim, validation_result in claims:
            staged, _ = await self.stage_extraction(
                ExtractionType.CLAIM, claim, source_id, validation_result,
                llm_model, llm_provider, auto_materialize=auto_materialize,
                commit=commit,
            )
            staged_extractions.append(staged)

        logger.info(
            "Staged batch of %d extractions (%d entities, %d relations, %d claims)",
            len(staged_extractions), len(entities), len(relations), len(claims),
        )
        return staged_extractions

    # =========================================================================
    # Review Operations
    # =========================================================================

    async def approve_extraction(
        self,
        extraction_id: UUID,
        reviewer_id: UUID,
        notes: str | None = None,
        auto_materialize: bool = True,
    ) -> MaterializationResult:
        """Approve a staged extraction and optionally materialize it."""
        staged = await load_staged_extraction(self.db, extraction_id)

        if not staged:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type="entity",
                error="Staged extraction not found",
            )

        reviewable = {ExtractionStatus.PENDING, ExtractionStatus.AUTO_VERIFIED}
        if staged.status not in reviewable:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
                error=f"Extraction already {staged.status.value}",
            )

        # If already materialized, just update status and commit atomically
        if staged.materialized_entity_id or staged.materialized_relation_id:
            apply_review_metadata(staged, reviewer_id, notes, approved=True)
            await self.db.commit()
            return MaterializationResult(
                success=True,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
                materialized_entity_id=staged.materialized_entity_id,
                materialized_relation_id=staged.materialized_relation_id,
            )

        if auto_materialize:
            # Keep status change and materialization in the same transaction so that
            # a materialization failure never leaves the extraction stuck in APPROVED.
            original_status = staged.status
            apply_review_metadata(staged, reviewer_id, notes, approved=True)
            result = await self.materialize_extraction(extraction_id, user_id=reviewer_id)
            if not result.success:
                # materialize_extraction rolled back; undo the in-memory status change
                staged.status = original_status
                staged.reviewed_by = None
                staged.reviewed_at = None
                staged.review_notes = None
            return result

        apply_review_metadata(staged, reviewer_id, notes, approved=True)
        await self.db.commit()
        return MaterializationResult(
            success=True,
            extraction_id=extraction_id,
            extraction_type=staged.extraction_type.value,
        )

    async def reject_extraction(
        self, extraction_id: UUID, reviewer_id: UUID, notes: str | None = None
    ) -> bool:
        """Reject a staged extraction."""
        staged = await load_staged_extraction(self.db, extraction_id)

        reviewable = {ExtractionStatus.PENDING, ExtractionStatus.AUTO_VERIFIED}
        if not staged or staged.status not in reviewable:
            return False

        apply_review_metadata(staged, reviewer_id, notes, approved=False)

        # Soft-delete the materialized entity or relation so it is hidden from
        # listings, search, and export.  The record itself is preserved for audit.
        if staged.materialized_entity_id:
            entity = await self.db.get(Entity, staged.materialized_entity_id)
            if entity:
                entity.is_rejected = True
        elif staged.materialized_relation_id:
            relation = await self.db.get(Relation, staged.materialized_relation_id)
            if relation:
                relation.is_rejected = True

        await self.db.commit()
        logger.info("Rejected extraction %s", extraction_id)
        return True

    async def get_extraction(self, extraction_id: UUID) -> StagedExtraction | None:
        """Load a single staged extraction by ID."""
        return await load_staged_extraction(self.db, extraction_id)

    async def delete_extraction(self, extraction_id: UUID) -> bool:
        """Delete a staged extraction by ID."""
        staged = await load_staged_extraction(self.db, extraction_id)
        if not staged:
            return False

        await self.db.delete(staged)
        await self.db.commit()
        logger.info("Deleted staged extraction %s", extraction_id)
        return True

    async def batch_review(
        self,
        extraction_ids: list[UUID],
        decision: str,  # "approve" or "reject"
        reviewer_id: UUID,
        notes: str | None = None,
    ) -> BatchReviewResponse:
        """Review multiple extractions at once."""
        succeeded = 0
        failed = []
        materialized_entities = []
        materialized_relations = []

        for extraction_id in extraction_ids:
            try:
                if decision == "approve":
                    result = await self.approve_extraction(
                        extraction_id, reviewer_id, notes, auto_materialize=True
                    )
                    if result.success:
                        succeeded += 1
                        if result.materialized_entity_id:
                            materialized_entities.append(result.materialized_entity_id)
                        if result.materialized_relation_id:
                            materialized_relations.append(result.materialized_relation_id)
                    else:
                        failed.append(extraction_id)
                else:  # reject
                    success = await self.reject_extraction(extraction_id, reviewer_id, notes)
                    if success:
                        succeeded += 1
                    else:
                        failed.append(extraction_id)
            except Exception as e:
                logger.error("Failed to review extraction %s: %s", extraction_id, e, exc_info=True)
                failed.append(extraction_id)

        return BatchReviewResponse(
            total_requested=len(extraction_ids),
            succeeded=succeeded,
            failed=len(failed),
            failed_ids=failed,
            materialized_entities=materialized_entities,
            materialized_relations=materialized_relations,
        )

    # =========================================================================
    # Materialization
    # =========================================================================

    async def materialize_extraction(
        self, extraction_id: UUID, user_id: UUID | None = None
    ) -> MaterializationResult:
        """Materialize an approved extraction into the knowledge graph."""
        staged = await load_staged_extraction(self.db, extraction_id)

        if not staged:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type="entity",
                error="Staged extraction not found",
            )

        if staged.status != ExtractionStatus.APPROVED:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
                error=f"Extraction not approved (status: {staged.status.value})",
            )

        try:
            if staged.extraction_type == ExtractionType.ENTITY:
                entity_id = await materialize_entity(self.db, staged, user_id=user_id)
                staged.materialized_entity_id = entity_id
                await self.db.commit()
                return MaterializationResult(
                    success=True,
                    extraction_id=extraction_id,
                    extraction_type="entity",
                    materialized_entity_id=entity_id,
                )

            elif staged.extraction_type == ExtractionType.RELATION:
                relation_id = await materialize_relation(self.db, staged, user_id=user_id)
                staged.materialized_relation_id = relation_id
                await self.db.commit()
                return MaterializationResult(
                    success=True,
                    extraction_id=extraction_id,
                    extraction_type="relation",
                    materialized_relation_id=relation_id,
                )

            else:  # CLAIM → materialized as a relation
                relation_id = await materialize_claim(self.db, staged, user_id=user_id)
                staged.materialized_relation_id = relation_id
                await self.db.commit()
                return MaterializationResult(
                    success=True,
                    extraction_id=extraction_id,
                    extraction_type="claim",
                    materialized_relation_id=relation_id,
                )

        except Exception as e:
            logger.error("Failed to materialize extraction %s: %s", extraction_id, e, exc_info=True)
            await self.db.rollback()
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
                error=str(e),
            )

    # =========================================================================
    # Querying and Statistics
    # =========================================================================

    async def list_extractions(
        self, filters: StagedExtractionFilters, *, include_claims: bool = True
    ) -> tuple[list[StagedExtraction], int]:
        """List staged extractions with filtering and pagination."""
        await self._refresh_structural_validation_for_unreviewed_relations(
            source_id=filters.source_id,
            include_relations=filters.extraction_type in (None, ExtractionType.RELATION),
        )
        return await list_review_extractions(self.db, filters, include_claims=include_claims)

    async def get_stats(self, *, include_claims: bool = True) -> ReviewStats:
        """Get review statistics."""
        await self._refresh_structural_validation_for_unreviewed_relations()
        return await get_review_stats(self.db, include_claims=include_claims)

    # =========================================================================
    # Auto-Commit
    # =========================================================================

    def _is_auto_commit_eligible(self, validation_result: ValidationResult) -> bool:
        return check_auto_commit_eligible(
            validation_result,
            self.auto_commit_enabled,
            self.auto_commit_threshold,
            self.require_no_flags_for_auto_commit,
        )

    async def _refresh_structural_validation_for_unreviewed_relations(
        self,
        *,
        source_id: UUID | None = None,
        include_relations: bool = True,
    ) -> None:
        if not include_relations:
            return

        stmt = select(StagedExtraction).where(
            StagedExtraction.extraction_type == ExtractionType.RELATION,
            StagedExtraction.status.in_([ExtractionStatus.PENDING, ExtractionStatus.AUTO_VERIFIED]),
        )
        if source_id is not None:
            stmt = stmt.where(StagedExtraction.source_id == source_id)

        result = await self.db.execute(stmt)
        staged_relations = list(result.scalars().all())
        changed = False

        for staged in staged_relations:
            structural_result = self._get_structural_validation_result(staged.extraction_data)
            if structural_result is None:
                continue

            merged_flags = list(dict.fromkeys([*(staged.validation_flags or []), *structural_result.flags]))
            next_status = (
                ExtractionStatus.PENDING
                if staged.status == ExtractionStatus.AUTO_VERIFIED
                else staged.status
            )

            if (
                staged.validation_score == structural_result.validation_score
                and staged.confidence_adjustment == structural_result.confidence_adjustment
                and staged.validation_flags == merged_flags
                and staged.auto_commit_eligible is False
                and staged.status == next_status
            ):
                continue

            staged.validation_score = structural_result.validation_score
            staged.confidence_adjustment = structural_result.confidence_adjustment
            staged.validation_flags = merged_flags
            staged.auto_commit_eligible = False
            staged.status = next_status
            changed = True

        if changed:
            await self.db.commit()

    def _get_structural_validation_result(
        self,
        extraction_data: dict[str, object] | None,
    ) -> ValidationResult | None:
        if not isinstance(extraction_data, dict):
            return None

        relation_type = extraction_data.get("relation_type")
        roles_payload = extraction_data.get("roles")
        text_span = extraction_data.get("text_span")
        notes = extraction_data.get("notes")

        if not isinstance(relation_type, str) or not isinstance(roles_payload, list):
            return None

        roles: list[ExtractedRole] = []
        for role_payload in roles_payload:
            if not isinstance(role_payload, dict):
                continue
            entity_slug = role_payload.get("entity_slug")
            role_type = role_payload.get("role_type")
            if not isinstance(entity_slug, str) or not isinstance(role_type, str):
                continue
            roles.append(ExtractedRole.model_construct(entity_slug=entity_slug, role_type=role_type))

        relation = ExtractedRelation.model_construct(
            relation_type=relation_type,
            roles=roles,
            confidence="medium",
            text_span=text_span if isinstance(text_span, str) else "",
            notes=notes if isinstance(notes, str) else None,
            scope=None,
            evidence_context=None,
        )
        return validate_relation_structure(relation)

    async def auto_commit_eligible_extractions(self) -> AutoCommitResponse:
        """Automatically commit all eligible pending extractions."""
        if not self.auto_commit_enabled:
            return AutoCommitResponse(
                status="success",
                auto_committed=0,
                message="Auto-commit is disabled",
            )
        return await run_auto_commit(self.db, self.auto_commit_threshold)
