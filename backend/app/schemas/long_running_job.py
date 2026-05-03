from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


JobKindLiteral = Literal["smart_discovery", "source_url_extraction"]
JobStatusLiteral = Literal["pending", "running", "succeeded", "failed"]


class JobStartResponse(BaseModel):
    job_id: UUID
    status: JobStatusLiteral


class LongRunningJobRead(BaseModel):
    id: UUID
    kind: JobKindLiteral
    status: JobStatusLiteral
    source_id: UUID | None = None
    request_payload: dict[str, Any]
    result_payload: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
