from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, UUIDMixin


class GraphCleaningDecision(Base, UUIDMixin):
    """Persisted admin decision for a graph-cleaning candidate."""

    __tablename__ = "graph_cleaning_decisions"
    __table_args__ = (
        UniqueConstraint(
            "candidate_type",
            "candidate_fingerprint",
            name="uq_graph_cleaning_decision_candidate",
        ),
    )

    candidate_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    candidate_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    action_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
