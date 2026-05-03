from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.long_running_job import LongRunningJobRead
from app.services.long_running_job_service import load_owned_job


router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=LongRunningJobRead)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LongRunningJobRead:
    job = await load_owned_job(db, job_id=job_id, user_id=current_user.id)
    return LongRunningJobRead(
        id=job.id,
        kind=job.kind.value,
        status=job.status.value,
        source_id=job.source_id,
        request_payload=job.request_payload,
        result_payload=job.result_payload,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )
