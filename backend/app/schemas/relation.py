from uuid import UUID
from typing import List, Optional, Literal
from app.schemas.base import Schema
from app.schemas.role import RoleWrite, RoleRead


class RelationWrite(Schema):
    source_id: UUID
    kind: str
    direction: str
    confidence: float
    roles: List[RoleWrite]
    notes: Optional[str] = None


class RelationRead(RelationWrite):
    id: UUID
    roles: List[RoleRead]