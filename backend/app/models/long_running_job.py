import datetime
import enum
from typing import Any
from uuid import UUID as PyUUID

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class LongRunningJobKind(str, enum.Enum):
    SMART_DISCOVERY = "smart_discovery"
    SOURCE_URL_EXTRACTION = "source_url_extraction"
    BULK_SOURCE_EXTRACTION = "bulk_source_extraction"


class LongRunningJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class LongRunningJob(Base, UUIDMixin, TimestampMixin):
    """Persisted status/result for mobile-resumable long-running frontend actions."""

    __tablename__ = "long_running_jobs"

    kind: Mapped[LongRunningJobKind] = mapped_column(
        SQLEnum(LongRunningJobKind, native_enum=False),
        nullable=False,
        index=True,
    )
    status: Mapped[LongRunningJobStatus] = mapped_column(
        SQLEnum(LongRunningJobStatus, native_enum=False),
        nullable=False,
        default=LongRunningJobStatus.PENDING,
        index=True,
    )
    user_id: Mapped[PyUUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[PyUUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
