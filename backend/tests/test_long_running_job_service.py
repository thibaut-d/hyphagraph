from uuid import uuid4

import pytest

from app.models.long_running_job import LongRunningJobKind, LongRunningJobStatus
from app.schemas.long_running_job import LongRunningJobRead
from app.services.long_running_job_service import create_job, load_owned_job, run_job


pytestmark = pytest.mark.asyncio


async def test_run_job_persists_success_result(db_session, test_user):
    job = await create_job(
        db_session,
        kind=LongRunningJobKind.SMART_DISCOVERY,
        user_id=test_user.id,
        request_payload={"entity_slugs": ["metformin"]},
    )

    async def operation(_db, _job):
        return {"ok": True}

    await run_job(db_session, job_id=job.id, operation=operation)

    loaded = await load_owned_job(db_session, job_id=job.id, user_id=test_user.id)
    assert loaded.status == LongRunningJobStatus.SUCCEEDED
    assert loaded.result_payload == {"ok": True}
    assert loaded.error_message is None
    assert loaded.started_at is not None
    assert loaded.finished_at is not None


async def test_run_job_persists_failure_without_raising(db_session, test_user):
    job = await create_job(
        db_session,
        kind=LongRunningJobKind.SOURCE_URL_EXTRACTION,
        user_id=test_user.id,
        source_id=None,
        request_payload={"url": "https://example.com"},
    )

    async def operation(_db, _job):
        raise RuntimeError("provider timeout")

    await run_job(db_session, job_id=job.id, operation=operation)

    loaded = await load_owned_job(db_session, job_id=job.id, user_id=test_user.id)
    assert loaded.status == LongRunningJobStatus.FAILED
    assert loaded.result_payload is None
    assert loaded.error_message == "provider timeout"
    assert loaded.finished_at is not None


async def test_load_owned_job_rejects_other_user(db_session, test_user):
    job = await create_job(
        db_session,
        kind=LongRunningJobKind.SMART_DISCOVERY,
        user_id=test_user.id,
        request_payload={"entity_slugs": ["metformin"]},
    )

    with pytest.raises(Exception):
        await load_owned_job(db_session, job_id=job.id, user_id=uuid4())


async def test_long_running_job_read_accepts_bulk_source_extraction_kind():
    LongRunningJobRead.model_validate(
        {
            "id": uuid4(),
            "kind": LongRunningJobKind.BULK_SOURCE_EXTRACTION.value,
            "status": LongRunningJobStatus.SUCCEEDED.value,
            "request_payload": {"search": "pain", "study_budget": 10},
            "result_payload": {"extracted_count": 1},
            "created_at": "2026-05-03T19:12:00Z",
            "updated_at": "2026-05-03T19:12:00Z",
        }
    )
