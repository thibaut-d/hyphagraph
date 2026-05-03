import datetime
import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.long_running_job import (
    LongRunningJob,
    LongRunningJobKind,
    LongRunningJobStatus,
)
from app.utils.errors import AppException, ErrorCode


logger = logging.getLogger(__name__)


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def json_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise TypeError(f"Job result must be a Pydantic model or dict, got {type(value).__name__}")


async def create_job(
    db: AsyncSession,
    *,
    kind: LongRunningJobKind,
    user_id: UUID,
    request_payload: dict[str, Any],
    source_id: UUID | None = None,
) -> LongRunningJob:
    job = LongRunningJob(
        kind=kind,
        status=LongRunningJobStatus.PENDING,
        user_id=user_id,
        source_id=source_id,
        request_payload=request_payload,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def load_owned_job(
    db: AsyncSession,
    *,
    job_id: UUID,
    user_id: UUID,
) -> LongRunningJob:
    result = await db.execute(
        select(LongRunningJob).where(
            LongRunningJob.id == job_id,
            LongRunningJob.user_id == user_id,
        )
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Job not found",
            context={"job_id": str(job_id)},
        )
    return job


async def run_job(
    db: AsyncSession,
    *,
    job_id: UUID,
    operation: Callable[[AsyncSession, LongRunningJob], Awaitable[Any]],
) -> None:
    job = await db.get(LongRunningJob, job_id)
    if job is None:
        logger.error("Cannot run missing job %s", job_id)
        return

    job.status = LongRunningJobStatus.RUNNING
    job.started_at = utcnow()
    job.updated_at = job.started_at
    await db.commit()

    try:
        result = await operation(db, job)
    except Exception as exc:
        await db.rollback()
        failed_job = await db.get(LongRunningJob, job_id)
        if failed_job is None:
            logger.exception("Job %s failed and disappeared", job_id)
            return
        now = utcnow()
        failed_job.status = LongRunningJobStatus.FAILED
        failed_job.error_message = str(exc) or type(exc).__name__
        failed_job.finished_at = now
        failed_job.updated_at = now
        await db.commit()
        logger.exception("Long-running job %s failed", job_id)
        return

    finished_job = await db.get(LongRunningJob, job_id)
    if finished_job is None:
        logger.error("Job %s completed but disappeared", job_id)
        return
    now = utcnow()
    finished_job.status = LongRunningJobStatus.SUCCEEDED
    finished_job.result_payload = json_payload(result)
    finished_job.error_message = None
    finished_job.finished_at = now
    finished_job.updated_at = now
    await db.commit()
