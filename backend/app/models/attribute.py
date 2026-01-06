from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Enum, DateTime, CheckConstraint, JSON
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID
from app.models.base import Base, UUIDMixin
import enum


class AttributeOwnerType(str, enum.Enum):
    """Type of object that owns an attribute"""
    ENTITY = "entity"
    RELATION = "relation"


class Attribute(Base, UUIDMixin):
    """
    Generic key-value attributes for entities or relations.

    Use cases:
    - External identifiers (DOI, PubMed ID, ATC codes, etc.)
    - URLs to external resources
    - Metadata that doesn't fit in main schema

    Rules:
    - Attributes MUST NOT encode multi-entity claims or causality
    - They are descriptive/qualifying only
    - Not versioned - updates replace previous value with timestamp
    """
    __tablename__ = "attributes"

    owner_type: Mapped[AttributeOwnerType] = mapped_column(
        Enum(AttributeOwnerType),
        nullable=False,
    )

    owner_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    key: Mapped[str] = mapped_column(String, nullable=False)

    # Value can be string, number, boolean, or JSON
    value: Mapped[dict | str | int | float | bool] = mapped_column(JSON, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "owner_type IN ('entity', 'relation')",
            name='ck_attribute_owner_type'
        ),
    )
