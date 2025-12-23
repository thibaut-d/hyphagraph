from uuid import UUID
from typing import Optional
from app.schemas.base import Schema


class SourceCreate(Schema):
    kind: str
    title: str
    year: int
    origin: Optional[str] = None
    url: Optional[str] = None
    trust_level: float


class SourceRead(Schema):
    id: UUID
    kind: str
    title: str
    year: int
    origin: Optional[str] = None
    url: Optional[str] = None
    trust_level: float