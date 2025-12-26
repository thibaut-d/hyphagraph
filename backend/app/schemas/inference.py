from uuid import UUID
from typing import Any, Optional
from app.schemas.base import Schema
from app.schemas.relation import RelationRead


class InferenceRead(Schema):
    entity_id: UUID
    relations_by_kind: dict[str, list[RelationRead]]