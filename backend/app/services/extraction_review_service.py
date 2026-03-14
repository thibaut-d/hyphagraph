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
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staged_extraction import StagedExtraction, ExtractionStatus, ExtractionType
from app.llm.schemas import ExtractedEntity, ExtractedRelation, ExtractedClaim
from app.schemas.staged_extraction import (
    StagedExtractionRead,
    StagedExtractionFilters,
    ReviewStats,
    MaterializationResult,
)
from app.services.extraction_validation_service import ValidationResult
from app.services.extraction_review.materialization import (
    materialize_entity,
    materialize_relation,
)
from app.services.extraction_review.queries import (
    apply_review_metadata,
    get_stats as get_review_stats,
    list_extractions as list_review_extractions,
    load_staged_extraction,
)

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
        """
        Initialize review service.

        Args:
            db: Database session
            auto_commit_enabled: Whether to enable auto-commit for high-confidence extractions
            auto_commit_threshold: Minimum validation_score for auto-commit (0.0-1.0)
            require_no_flags_for_auto_commit: If True, auto-commit only when validation_flags is empty
        """
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
    ) -> tuple[StagedExtraction, UUID | None]:
        """
        Create extraction metadata and optionally materialize.

        NEW WORKFLOW: Materializes immediately by default, sets status based on validation.
        - High confidence → status="auto_verified", materialized
        - Uncertain → status="pending", materialized but flagged for review

        Args:
            extraction_type: Type of extraction
            extraction_data: The extracted data (entity/relation/claim)
            source_id: Source document ID
            validation_result: Validation metadata
            llm_model: LLM model used
            llm_provider: LLM provider
            auto_materialize: Whether to materialize immediately (default True)

        Returns:
            Tuple of (StagedExtraction record, materialized_id)
        """
        # Determine status based on validation
        is_high_confidence = self._is_auto_commit_eligible(validation_result)
        initial_status = (
            ExtractionStatus.AUTO_VERIFIED if is_high_confidence else ExtractionStatus.PENDING
        )

        # Create staged extraction record
        staged = StagedExtraction(
            extraction_type=extraction_type,
            status=initial_status,
            source_id=source_id,
            extraction_data=extraction_data.model_dump(),
            validation_score=validation_result.validation_score,
            confidence_adjustment=validation_result.confidence_adjustment,
            validation_flags=validation_result.flags,
            matched_span=validation_result.matched_span,
            llm_model=llm_model,
            llm_provider=llm_provider,
            auto_commit_eligible=is_high_confidence,
            auto_commit_threshold=self.auto_commit_threshold if self.auto_commit_enabled else None,
        )

        self.db.add(staged)
        await self.db.flush()  # Get ID without committing

        # Materialize immediately if requested
        materialized_id = None
        if auto_materialize:
            if extraction_type == ExtractionType.ENTITY:
                entity_id = await self._materialize_entity(staged)
                staged.materialized_entity_id = entity_id
                materialized_id = entity_id
            elif extraction_type == ExtractionType.RELATION:
                relation_id = await self._materialize_relation(staged)
                staged.materialized_relation_id = relation_id
                materialized_id = relation_id
            # Claims not yet supported for materialization

        await self.db.commit()
        await self.db.refresh(staged)

        logger.info(
            f"Created {extraction_type} extraction (ID: {staged.id}, "
            f"status: {staged.status}, score: {validation_result.validation_score:.2f}, "
            f"materialized: {materialized_id is not None})"
        )

        return staged, materialized_id

    async def stage_batch(
        self,
        entities: list[tuple[ExtractedEntity, ValidationResult]],
        relations: list[tuple[ExtractedRelation, ValidationResult]],
        claims: list[tuple[ExtractedClaim, ValidationResult]],
        source_id: UUID,
        llm_model: str | None = None,
        llm_provider: str | None = None,
    ) -> list[StagedExtraction]:
        """
        Stage a batch of extractions.

        Args:
            entities: List of (entity, validation_result) tuples
            relations: List of (relation, validation_result) tuples
            claims: List of (claim, validation_result) tuples
            source_id: Source document ID
            llm_model: LLM model used
            llm_provider: LLM provider

        Returns:
            List of created StagedExtraction records
        """
        staged_extractions = []

        # Stage entities
        for entity, validation_result in entities:
            staged, entity_id = await self.stage_extraction(
                extraction_type=ExtractionType.ENTITY,
                extraction_data=entity,
                source_id=source_id,
                validation_result=validation_result,
                llm_model=llm_model,
                llm_provider=llm_provider,
            )
            staged_extractions.append(staged)

        # Stage relations
        for relation, validation_result in relations:
            staged, relation_id = await self.stage_extraction(
                extraction_type=ExtractionType.RELATION,
                extraction_data=relation,
                source_id=source_id,
                validation_result=validation_result,
                llm_model=llm_model,
                llm_provider=llm_provider,
            )
            staged_extractions.append(staged)

        # Stage claims
        for claim, validation_result in claims:
            staged, _ = await self.stage_extraction(
                extraction_type=ExtractionType.CLAIM,
                extraction_data=claim,
                source_id=source_id,
                validation_result=validation_result,
                llm_model=llm_model,
                llm_provider=llm_provider,
            )
            staged_extractions.append(staged)

        logger.info(
            f"Staged batch of {len(staged_extractions)} extractions "
            f"({len(entities)} entities, {len(relations)} relations, {len(claims)} claims)"
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
        """
        Approve a staged extraction and optionally materialize it.

        Args:
            extraction_id: ID of staged extraction
            reviewer_id: ID of reviewing user
            notes: Optional review notes
            auto_materialize: Whether to automatically materialize the extraction

        Returns:
            MaterializationResult with success status and created IDs
        """
        # Load staged extraction
        staged = await load_staged_extraction(self.db, extraction_id)

        if not staged:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type="entity",  # Dummy value
                error="Staged extraction not found",
            )

        if staged.status != ExtractionStatus.PENDING:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
                error=f"Extraction already {staged.status.value}",
            )

        # Update status
        apply_review_metadata(staged, reviewer_id, notes, approved=True)

        await self.db.commit()

        # Materialize if requested
        if auto_materialize:
            if staged.materialized_entity_id or staged.materialized_relation_id:
                return MaterializationResult(
                    success=True,
                    extraction_id=extraction_id,
                    extraction_type=staged.extraction_type.value,
                    materialized_entity_id=staged.materialized_entity_id,
                    materialized_relation_id=staged.materialized_relation_id,
                )
            return await self.materialize_extraction(extraction_id)
        else:
            return MaterializationResult(
                success=True,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
            )

    async def reject_extraction(
        self, extraction_id: UUID, reviewer_id: UUID, notes: str | None = None
    ) -> bool:
        """
        Reject a staged extraction.

        Args:
            extraction_id: ID of staged extraction
            reviewer_id: ID of reviewing user
            notes: Optional review notes

        Returns:
            True if successful, False otherwise
        """
        staged = await load_staged_extraction(self.db, extraction_id)

        if not staged or staged.status != ExtractionStatus.PENDING:
            return False

        apply_review_metadata(staged, reviewer_id, notes, approved=False)

        await self.db.commit()
        logger.info(f"Rejected extraction {extraction_id}")
        return True

    async def batch_review(
        self,
        extraction_ids: list[UUID],
        decision: str,  # "approve" or "reject"
        reviewer_id: UUID,
        notes: str | None = None,
    ) -> dict:
        """
        Review multiple extractions at once.

        Args:
            extraction_ids: List of extraction IDs to review
            decision: "approve" or "reject"
            reviewer_id: ID of reviewing user
            notes: Optional notes applied to all

        Returns:
            Dict with success/failure counts and IDs
        """
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
                logger.error(f"Failed to review extraction {extraction_id}: {e}")
                failed.append(extraction_id)

        return {
            "total_requested": len(extraction_ids),
            "succeeded": succeeded,
            "failed": len(failed),
            "failed_ids": failed,
            "materialized_entities": materialized_entities,
            "materialized_relations": materialized_relations,
        }

    # =========================================================================
    # Materialization
    # =========================================================================

    async def materialize_extraction(self, extraction_id: UUID) -> MaterializationResult:
        """
        Materialize an approved extraction into the knowledge graph.

        Creates Entity/Relation records from the staged extraction data.

        Args:
            extraction_id: ID of staged extraction to materialize

        Returns:
            MaterializationResult with created IDs
        """
        # Load staged extraction
        staged = await load_staged_extraction(self.db, extraction_id)

        if not staged:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type="entity",  # Dummy
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
                entity_id = await self._materialize_entity(staged)
                staged.materialized_entity_id = entity_id
                await self.db.commit()

                return MaterializationResult(
                    success=True,
                    extraction_id=extraction_id,
                    extraction_type="entity",
                    materialized_entity_id=entity_id,
                )

            elif staged.extraction_type == ExtractionType.RELATION:
                relation_id = await self._materialize_relation(staged)
                staged.materialized_relation_id = relation_id
                await self.db.commit()

                return MaterializationResult(
                    success=True,
                    extraction_id=extraction_id,
                    extraction_type="relation",
                    materialized_relation_id=relation_id,
                )

            else:  # CLAIM
                # Claims are not yet implemented in the knowledge graph
                return MaterializationResult(
                    success=False,
                    extraction_id=extraction_id,
                    extraction_type="claim",
                    error="Claim materialization not yet implemented",
                )

        except Exception as e:
            logger.error(f"Failed to materialize extraction {extraction_id}: {e}")
            await self.db.rollback()
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
                error=str(e),
            )

    async def _materialize_entity(self, staged: StagedExtraction) -> UUID:
        """
        Create Entity + EntityRevision from staged extraction.

        Args:
            staged: Staged extraction with type=ENTITY

        Returns:
            Created entity ID
        """
        return await materialize_entity(self.db, staged)

    async def _materialize_relation(self, staged: StagedExtraction) -> UUID:
        """
        Create Relation + RelationRevision + RoleRevisions from staged extraction.

        Args:
            staged: Staged extraction with type=RELATION

        Returns:
            Created relation ID
        """
        return await materialize_relation(self.db, staged)

    # =========================================================================
    # Querying and Statistics
    # =========================================================================

    async def list_extractions(
        self, filters: StagedExtractionFilters
    ) -> tuple[list[StagedExtraction], int]:
        """
        List staged extractions with filtering and pagination.

        Args:
            filters: Query filters and pagination params

        Returns:
            Tuple of (extractions, total_count)
        """
        return await list_review_extractions(self.db, filters)

    async def get_stats(self) -> ReviewStats:
        """
        Get review statistics.

        Returns:
            ReviewStats with counts and metrics
        """
        return await get_review_stats(self.db)

    # =========================================================================
    # Auto-Commit Logic
    # =========================================================================

    def _is_auto_commit_eligible(self, validation_result: ValidationResult) -> bool:
        """
        Determine if an extraction is eligible for auto-commit.

        Args:
            validation_result: Validation metadata

        Returns:
            True if eligible for auto-commit, False otherwise
        """
        if not self.auto_commit_enabled:
            return False

        # Check validation score threshold
        if validation_result.validation_score < self.auto_commit_threshold:
            return False

        # Check for validation flags if required
        if self.require_no_flags_for_auto_commit and len(validation_result.flags) > 0:
            return False

        return True

    async def auto_commit_eligible_extractions(self) -> dict:
        """
        Automatically commit all eligible pending extractions.

        Returns:
            Dict with counts of auto-committed extractions
        """
        if not self.auto_commit_enabled:
            return {"auto_committed": 0, "message": "Auto-commit is disabled"}

        # Find eligible pending extractions
        result = await self.db.execute(
            select(StagedExtraction)
            .where(StagedExtraction.status == ExtractionStatus.PENDING)
            .where(StagedExtraction.auto_commit_eligible == True)
        )
        eligible = result.scalars().all()

        if not eligible:
            return {"auto_committed": 0, "message": "No eligible extractions found"}

        # Auto-approve and materialize
        materialized_count = 0
        failed_count = 0

        for staged in eligible:
            try:
                # Mark as approved (system auto-approval, no reviewer)
                staged.status = ExtractionStatus.APPROVED
                staged.reviewed_at = datetime.utcnow()
                staged.review_notes = "Auto-approved by system (high validation score)"
                await self.db.commit()

                # Materialize
                result = await self.materialize_extraction(staged.id)
                if result.success:
                    materialized_count += 1
                else:
                    failed_count += 1
                    logger.warning(
                        f"Failed to materialize auto-approved extraction {staged.id}: {result.error}"
                    )

            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to auto-commit extraction {staged.id}: {e}")
                await self.db.rollback()

        logger.info(
            f"Auto-committed {materialized_count}/{len(eligible)} eligible extractions "
            f"({failed_count} failed)"
        )

        return {
            "auto_committed": materialized_count,
            "failed": failed_count,
            "total_eligible": len(eligible),
        }
