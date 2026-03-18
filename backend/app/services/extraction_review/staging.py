"""Staging helpers for the extraction review workflow."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.schemas import ExtractedClaim, ExtractedEntity, ExtractedRelation
from app.models.staged_extraction import ExtractionStatus, ExtractionType, StagedExtraction
from app.services.extraction_review.materialization import materialize_entity, materialize_relation
from app.services.extraction_validation_service import ValidationResult

logger = logging.getLogger(__name__)


async def create_staged_extraction(
    db: AsyncSession,
    extraction_type: ExtractionType,
    extraction_data: ExtractedEntity | ExtractedRelation | ExtractedClaim,
    source_id: UUID,
    validation_result: ValidationResult,
    llm_model: str | None,
    llm_provider: str | None,
    is_high_confidence: bool,
    auto_commit_threshold: float | None,
    auto_materialize: bool,
) -> tuple[StagedExtraction, UUID | None]:
    """Create a staged extraction record and optionally materialize it immediately."""
    # AUTO_VERIFIED only when materializing inline; deferred high-confidence items stay PENDING
    # so run_auto_commit can find and materialize them later.
    initial_status = (
        ExtractionStatus.AUTO_VERIFIED if (is_high_confidence and auto_materialize)
        else ExtractionStatus.PENDING
    )

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
        auto_commit_threshold=auto_commit_threshold,
    )

    db.add(staged)
    await db.flush()

    materialized_id = None
    if auto_materialize:
        if extraction_type == ExtractionType.ENTITY:
            entity_id = await materialize_entity(db, staged)
            staged.materialized_entity_id = entity_id
            materialized_id = entity_id
        elif extraction_type == ExtractionType.RELATION:
            relation_id = await materialize_relation(db, staged)
            staged.materialized_relation_id = relation_id
            materialized_id = relation_id
        # Claims not yet supported for materialization

    await db.commit()
    await db.refresh(staged)

    logger.info(
        "Created %s extraction (ID: %s, status: %s, score: %.2f, materialized: %s)",
        extraction_type,
        staged.id,
        staged.status,
        validation_result.validation_score,
        materialized_id is not None,
    )

    return staged, materialized_id
