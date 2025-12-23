from uuid import UUID
from typing import Any, Optional
from app.schemas.base import Schema


class InferenceRead(Schema):
    id: UUID
    scope_hash: str
    result: Any
    uncertainty: Optional[float] = None