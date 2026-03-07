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
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.staged_extraction import StagedExtraction, ExtractionStatus, ExtractionType
from app.models.entity import Entity
from app.models.entity_revision import EntityRevision
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision
from app.models.user import User
from app.llm.schemas import ExtractedEntity, ExtractedRelation, ExtractedClaim
from app.schemas.staged_extraction import (
    StagedExtractionRead,
    StagedExtractionFilters,
    ReviewStats,
    MaterializationResult,
)
from app.services.extraction_validation_service import ValidationResult

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
        require_no_flags_for_auto_commit: bool = True
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
    ) -> StagedExtraction:
        """
        Stage an extraction for review.

        Args:
            extraction_type: Type of extraction
            extraction_data: The extracted data (entity/relation/claim)
            source_id: Source document ID
            validation_result: Validation metadata
            llm_model: LLM model used
            llm_provider: LLM provider

        Returns:
            Created StagedExtraction record
        """
        # Determine if eligible for auto-commit
        is_auto_commit_eligible = self._is_auto_commit_eligible(validation_result)

        staged = StagedExtraction(
            extraction_type=extraction_type,
            status=ExtractionStatus.PENDING,
            source_id=source_id,
            extraction_data=extraction_data.model_dump(),
            validation_score=validation_result.validation_score,
            confidence_adjustment=validation_result.confidence_adjustment,
            validation_flags=validation_result.flags,
            matched_span=validation_result.matched_span,
            llm_model=llm_model,
            llm_provider=llm_provider,
            auto_commit_eligible=is_auto_commit_eligible,
            auto_commit_threshold=self.auto_commit_threshold if self.auto_commit_enabled else None,
        )

        self.db.add(staged)
        await self.db.commit()
        await self.db.refresh(staged)

        logger.info(
            f"Staged {extraction_type} extraction (ID: {staged.id}, "
            f"score: {validation_result.validation_score:.2f}, "
            f"auto-commit eligible: {is_auto_commit_eligible})"
        )

        return staged

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
            staged = await self.stage_extraction(
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
            staged = await self.stage_extraction(
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
            staged = await self.stage_extraction(
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
        auto_materialize: bool = True
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
        result = await self.db.execute(
            select(StagedExtraction).where(StagedExtraction.id == extraction_id)
        )
        staged = result.scalar_one_or_none()

        if not staged:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type="entity",  # Dummy value
                error="Staged extraction not found"
            )

        if staged.status != ExtractionStatus.PENDING:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
                error=f"Extraction already {staged.status.value}"
            )

        # Update status
        staged.status = ExtractionStatus.APPROVED
        staged.reviewed_by = reviewer_id
        staged.reviewed_at = datetime.utcnow()
        staged.review_notes = notes

        await self.db.commit()

        # Materialize if requested
        if auto_materialize:
            return await self.materialize_extraction(extraction_id)
        else:
            return MaterializationResult(
                success=True,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value
            )

    async def reject_extraction(
        self,
        extraction_id: UUID,
        reviewer_id: UUID,
        notes: str | None = None
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
        result = await self.db.execute(
            select(StagedExtraction).where(StagedExtraction.id == extraction_id)
        )
        staged = result.scalar_one_or_none()

        if not staged or staged.status != ExtractionStatus.PENDING:
            return False

        staged.status = ExtractionStatus.REJECTED
        staged.reviewed_by = reviewer_id
        staged.reviewed_at = datetime.utcnow()
        staged.review_notes = notes

        await self.db.commit()
        logger.info(f"Rejected extraction {extraction_id}")
        return True

    async def batch_review(
        self,
        extraction_ids: list[UUID],
        decision: str,  # "approve" or "reject"
        reviewer_id: UUID,
        notes: str | None = None
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
                        extraction_id,
                        reviewer_id,
                        notes,
                        auto_materialize=True
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
        result = await self.db.execute(
            select(StagedExtraction).where(StagedExtraction.id == extraction_id)
        )
        staged = result.scalar_one_or_none()

        if not staged:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type="entity",  # Dummy
                error="Staged extraction not found"
            )

        if staged.status != ExtractionStatus.APPROVED:
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
                error=f"Extraction not approved (status: {staged.status.value})"
            )

        try:
            if staged.extraction_type == ExtractionType.ENTITY:
                entity_id = await self._materialize_entity(staged)
                staged.status = ExtractionStatus.MATERIALIZED
                staged.materialized_entity_id = entity_id
                await self.db.commit()

                return MaterializationResult(
                    success=True,
                    extraction_id=extraction_id,
                    extraction_type="entity",
                    materialized_entity_id=entity_id
                )

            elif staged.extraction_type == ExtractionType.RELATION:
                relation_id = await self._materialize_relation(staged)
                staged.status = ExtractionStatus.MATERIALIZED
                staged.materialized_relation_id = relation_id
                await self.db.commit()

                return MaterializationResult(
                    success=True,
                    extraction_id=extraction_id,
                    extraction_type="relation",
                    materialized_relation_id=relation_id
                )

            else:  # CLAIM
                # Claims are not yet implemented in the knowledge graph
                return MaterializationResult(
                    success=False,
                    extraction_id=extraction_id,
                    extraction_type="claim",
                    error="Claim materialization not yet implemented"
                )

        except Exception as e:
            logger.error(f"Failed to materialize extraction {extraction_id}: {e}")
            await self.db.rollback()
            return MaterializationResult(
                success=False,
                extraction_id=extraction_id,
                extraction_type=staged.extraction_type.value,
                error=str(e)
            )

    async def _materialize_entity(self, staged: StagedExtraction) -> UUID:
        """
        Create Entity + EntityRevision from staged extraction.

        Args:
            staged: Staged extraction with type=ENTITY

        Returns:
            Created entity ID
        """
        # Parse extraction data
        entity_data = ExtractedEntity(**staged.extraction_data)

        # Create Entity base record
        entity = Entity()
        self.db.add(entity)
        await self.db.flush()

        # Create EntityRevision with extracted data
        revision = EntityRevision(
            entity_id=entity.id,
            slug=entity_data.slug,
            summary=entity_data.summary or "",
            category=entity_data.category,
            is_deleted=False,
        )
        self.db.add(revision)
        await self.db.flush()

        logger.info(f"Materialized entity {entity.id} from staged extraction {staged.id}")
        return entity.id

    async def _materialize_relation(self, staged: StagedExtraction) -> UUID:
        """
        Create Relation + RelationRevision + RoleRevisions from staged extraction.

        Args:
            staged: Staged extraction with type=RELATION

        Returns:
            Created relation ID
        """
        # Parse extraction data
        relation_data = ExtractedRelation(**staged.extraction_data)

        # Create Relation base record
        relation = Relation(source_id=staged.source_id)
        self.db.add(relation)
        await self.db.flush()

        # Create RelationRevision
        # Note: Confidence from LLM is string ("high"/"medium"/"low"), convert to float
        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.5}
        confidence_value = confidence_map.get(relation_data.confidence, 0.7)

        # Apply validation adjustment
        final_confidence = confidence_value * staged.confidence_adjustment

        revision = RelationRevision(
            relation_id=relation.id,
            kind=relation_data.relation_type,
            confidence=final_confidence,
            context=relation_data.text_span or "",
            is_deleted=False,
        )
        self.db.add(revision)
        await self.db.flush()

        # Create role revisions
        # Note: We need to look up entity IDs by slug
        for role_data in relation_data.roles:
            # Find entity by slug
            entity_result = await self.db.execute(
                select(EntityRevision)
                .where(EntityRevision.slug == role_data["entity_slug"])
                .where(EntityRevision.is_deleted == False)
                .order_by(EntityRevision.created_at.desc())
                .limit(1)
            )
            entity_revision = entity_result.scalar_one_or_none()

            if not entity_revision:
                logger.warning(
                    f"Entity with slug '{role_data['entity_slug']}' not found, "
                    f"skipping role in relation {relation.id}"
                )
                continue

            role_revision = RelationRoleRevision(
                revision_id=revision.id,
                entity_id=entity_revision.entity_id,
                role_type=role_data["role_type"],
            )
            self.db.add(role_revision)

        await self.db.flush()

        logger.info(f"Materialized relation {relation.id} from staged extraction {staged.id}")
        return relation.id

    # =========================================================================
    # Querying and Statistics
    # =========================================================================

    async def list_extractions(
        self,
        filters: StagedExtractionFilters
    ) -> tuple[list[StagedExtraction], int]:
        """
        List staged extractions with filtering and pagination.

        Args:
            filters: Query filters and pagination params

        Returns:
            Tuple of (extractions, total_count)
        """
        # Build query
        query = select(StagedExtraction)

        # Apply filters
        conditions = []
        if filters.status:
            conditions.append(StagedExtraction.status == filters.status)
        if filters.extraction_type:
            conditions.append(StagedExtraction.extraction_type == filters.extraction_type)
        if filters.source_id:
            conditions.append(StagedExtraction.source_id == filters.source_id)
        if filters.min_validation_score is not None:
            conditions.append(StagedExtraction.validation_score >= filters.min_validation_score)
        if filters.max_validation_score is not None:
            conditions.append(StagedExtraction.validation_score <= filters.max_validation_score)
        if filters.has_flags is not None:
            if filters.has_flags:
                conditions.append(func.jsonb_array_length(StagedExtraction.validation_flags) > 0)
            else:
                conditions.append(func.jsonb_array_length(StagedExtraction.validation_flags) == 0)
        if filters.auto_commit_eligible is not None:
            conditions.append(StagedExtraction.auto_commit_eligible == filters.auto_commit_eligible)

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(StagedExtraction)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting
        if filters.sort_by == "created_at":
            order_col = StagedExtraction.created_at
        elif filters.sort_by == "validation_score":
            order_col = StagedExtraction.validation_score
        else:  # confidence_adjustment
            order_col = StagedExtraction.confidence_adjustment

        if filters.sort_order == "desc":
            query = query.order_by(order_col.desc())
        else:
            query = query.order_by(order_col.asc())

        # Apply pagination
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        # Execute
        result = await self.db.execute(query)
        extractions = result.scalars().all()

        return list(extractions), total

    async def get_stats(self) -> ReviewStats:
        """
        Get review statistics.

        Returns:
            ReviewStats with counts and metrics
        """
        # Count by status
        status_counts = await self.db.execute(
            select(
                StagedExtraction.status,
                func.count(StagedExtraction.id)
            ).group_by(StagedExtraction.status)
        )
        status_map = {row[0]: row[1] for row in status_counts}

        total_pending = status_map.get(ExtractionStatus.PENDING, 0)
        total_approved = status_map.get(ExtractionStatus.APPROVED, 0)
        total_rejected = status_map.get(ExtractionStatus.REJECTED, 0)
        total_materialized = status_map.get(ExtractionStatus.MATERIALIZED, 0)

        # Count pending by type
        type_counts = await self.db.execute(
            select(
                StagedExtraction.extraction_type,
                func.count(StagedExtraction.id)
            )
            .where(StagedExtraction.status == ExtractionStatus.PENDING)
            .group_by(StagedExtraction.extraction_type)
        )
        type_map = {row[0]: row[1] for row in type_counts}

        pending_entities = type_map.get(ExtractionType.ENTITY, 0)
        pending_relations = type_map.get(ExtractionType.RELATION, 0)
        pending_claims = type_map.get(ExtractionType.CLAIM, 0)

        # Quality metrics for pending
        quality_result = await self.db.execute(
            select(
                func.avg(StagedExtraction.validation_score),
                func.count(StagedExtraction.id).filter(StagedExtraction.validation_score >= 0.9),
                func.count(StagedExtraction.id).filter(
                    func.jsonb_array_length(StagedExtraction.validation_flags) > 0
                )
            )
            .where(StagedExtraction.status == ExtractionStatus.PENDING)
        )
        quality_row = quality_result.one()
        avg_score = float(quality_row[0] or 0.0)
        high_confidence_count = int(quality_row[1] or 0)
        flagged_count = int(quality_row[2] or 0)

        return ReviewStats(
            total_pending=total_pending,
            total_approved=total_approved,
            total_rejected=total_rejected,
            total_materialized=total_materialized,
            pending_entities=pending_entities,
            pending_relations=pending_relations,
            pending_claims=pending_claims,
            avg_validation_score=avg_score,
            high_confidence_count=high_confidence_count,
            flagged_count=flagged_count,
        )

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
                    logger.warning(f"Failed to materialize auto-approved extraction {staged.id}: {result.error}")

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
