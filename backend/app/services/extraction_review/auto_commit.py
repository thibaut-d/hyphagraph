"""Auto-commit decision and execution helpers for extraction review."""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staged_extraction import ExtractionStatus, ExtractionType, StagedExtraction
from app.schemas.staged_extraction import AutoCommitResponse
from app.services.extraction_review.materialization import materialize_claim, materialize_entity, materialize_relation
from app.services.extraction_validation_service import ValidationResult

logger = logging.getLogger(__name__)


def check_auto_commit_eligible(
    validation_result: ValidationResult,
    auto_commit_enabled: bool,
    auto_commit_threshold: float,
    require_no_flags: bool,
) -> bool:
    """Return True if the validation result meets the auto-commit criteria."""
    if not auto_commit_enabled:
        return False
    if validation_result.validation_score < auto_commit_threshold:
        return False
    if require_no_flags and len(validation_result.flags) > 0:
        return False
    return True


async def run_auto_commit(db: AsyncSession, auto_commit_threshold: float) -> AutoCommitResponse:
    """Find all eligible pending extractions and auto-approve + materialize them."""
    result = await db.execute(
        select(StagedExtraction)
        .where(StagedExtraction.status == ExtractionStatus.PENDING)
        .where(StagedExtraction.auto_commit_eligible == True)  # noqa: E712
    )
    eligible = list(result.scalars().all())

    if not eligible:
        return AutoCommitResponse(
            status="success",
            auto_committed=0,
            message="No eligible extractions found",
        )

    materialized_count = 0
    failed_count = 0

    for staged in eligible:
        try:
            staged.status = ExtractionStatus.APPROVED
            staged.reviewed_at = datetime.utcnow()
            staged.review_notes = "Auto-approved by system (high validation score)"
            await db.commit()

            if await _materialize_approved(db, staged):
                materialized_count += 1
            else:
                failed_count += 1
                logger.warning("Failed to materialize auto-approved extraction %s", staged.id)

        except Exception as e:
            failed_count += 1
            logger.error("Failed to auto-commit extraction %s: %s", staged.id, e, exc_info=True)
            await db.rollback()

    logger.info(
        "Auto-committed %d/%d eligible extractions (%d failed)",
        materialized_count,
        len(eligible),
        failed_count,
    )

    return AutoCommitResponse(
        status="success",
        auto_committed=materialized_count,
        failed=failed_count,
        total_eligible=len(eligible),
    )


async def _materialize_approved(db: AsyncSession, staged: StagedExtraction) -> bool:
    """Materialize a single auto-approved staged extraction. Returns True on success."""
    try:
        if staged.extraction_type == ExtractionType.ENTITY:
            entity_id = await materialize_entity(db, staged)
            staged.materialized_entity_id = entity_id
            await db.commit()
            return True
        elif staged.extraction_type == ExtractionType.RELATION:
            relation_id = await materialize_relation(db, staged)
            staged.materialized_relation_id = relation_id
            await db.commit()
            return True
        elif staged.extraction_type == ExtractionType.CLAIM:
            relation_id = await materialize_claim(db, staged)
            staged.materialized_relation_id = relation_id
            await db.commit()
            return True
        return False
    except Exception as e:
        logger.error("Materialization failed for extraction %s: %s", staged.id, e, exc_info=True)
        await db.rollback()
        return False
