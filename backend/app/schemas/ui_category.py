"""Schemas for UI category management."""
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import Field
from app.schemas.base import Schema


class UICategoryWrite(Schema):
    """Schema for creating or updating a UI category."""
    slug: str = Field(min_length=1, max_length=100, description="Unique slug identifier")
    labels: dict[str, str] = Field(description='i18n labels e.g. {"en": "Drugs", "fr": "Médicaments"}')
    description: Optional[dict[str, str]] = Field(None, description="i18n descriptions")
    order: int = Field(0, ge=0, description="Display order (lower = first)")


class UICategoryRead(Schema):
    """Schema for reading a UI category."""
    id: UUID
    slug: str
    labels: dict[str, str]
    description: Optional[dict[str, str]] = None
    order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
