from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.staged_extraction import ExtractionStatus, ExtractionType, StagedExtraction
from app.schemas.staged_extraction import ReviewStats, StagedExtractionFilters


async def load_staged_extraction(
    db: AsyncSession, extraction_id: UUID
) -> StagedExtraction | None:
    result = await db.execute(select(StagedExtraction).where(StagedExtraction.id == extraction_id))
    return result.scalar_one_or_none()


async def list_extractions(
    db: AsyncSession, filters: StagedExtractionFilters
) -> tuple[list[StagedExtraction], int]:
    query = select(StagedExtraction)
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
        conditions.append(
            func.json_array_length(StagedExtraction.validation_flags) > 0
            if filters.has_flags
            else func.json_array_length(StagedExtraction.validation_flags) == 0
        )
    if filters.auto_commit_eligible is not None:
        conditions.append(StagedExtraction.auto_commit_eligible == filters.auto_commit_eligible)

    if conditions:
        query = query.where(and_(*conditions))

    count_query = select(func.count()).select_from(StagedExtraction)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = (await db.execute(count_query)).scalar() or 0

    order_col = {
        "created_at": StagedExtraction.created_at,
        "validation_score": StagedExtraction.validation_score,
    }.get(filters.sort_by, StagedExtraction.confidence_adjustment)
    query = query.order_by(order_col.desc() if filters.sort_order == "desc" else order_col.asc())

    offset = (filters.page - 1) * filters.page_size
    result = await db.execute(query.offset(offset).limit(filters.page_size))
    return list(result.scalars().all()), total


async def get_stats(db: AsyncSession) -> ReviewStats:
    status_counts = await db.execute(
        select(StagedExtraction.status, func.count(StagedExtraction.id)).group_by(StagedExtraction.status)
    )
    status_map = {row[0]: row[1] for row in status_counts}

    type_counts = await db.execute(
        select(StagedExtraction.extraction_type, func.count(StagedExtraction.id))
        .where(StagedExtraction.status == ExtractionStatus.PENDING)
        .group_by(StagedExtraction.extraction_type)
    )
    type_map = {row[0]: row[1] for row in type_counts}

    quality_row = (
        await db.execute(
            select(
                func.avg(StagedExtraction.validation_score),
                func.count(StagedExtraction.id).filter(StagedExtraction.validation_score >= 0.9),
                func.count(StagedExtraction.id).filter(
                    func.json_array_length(StagedExtraction.validation_flags) > 0
                ),
            ).where(StagedExtraction.status == ExtractionStatus.PENDING)
        )
    ).one()

    return ReviewStats(
        total_pending=status_map.get(ExtractionStatus.PENDING, 0),
        total_approved=status_map.get(ExtractionStatus.APPROVED, 0),
        total_rejected=status_map.get(ExtractionStatus.REJECTED, 0),
        total_auto_verified=status_map.get(ExtractionStatus.AUTO_VERIFIED, 0),
        pending_entities=type_map.get(ExtractionType.ENTITY, 0),
        pending_relations=type_map.get(ExtractionType.RELATION, 0),
        pending_claims=type_map.get(ExtractionType.CLAIM, 0),
        avg_validation_score=float(quality_row[0] or 0.0),
        high_confidence_count=int(quality_row[1] or 0),
        flagged_count=int(quality_row[2] or 0),
    )


def apply_review_metadata(staged: StagedExtraction, reviewer_id: UUID, notes: str | None, approved: bool) -> None:
    staged.status = ExtractionStatus.APPROVED if approved else ExtractionStatus.REJECTED
    staged.reviewed_by = reviewer_id
    staged.reviewed_at = datetime.utcnow()
    staged.review_notes = notes
