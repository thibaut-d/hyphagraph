from uuid import UUID
from app.schemas.base import Schema


class RoleWrite(Schema):
    entity_id: UUID
    role_type: str


class RoleRead(RoleWrite):
    entity_id: UUID