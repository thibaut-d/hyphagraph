from uuid import UUID
from typing import Optional, List
from app.schemas.base import Schema


class EntityWrite(Schema):
    kind: str
    label: str
    synonyms: List[str] = []
    ontology_ref: Optional[str] = None


class EntityRead(EntityWrite):
    id: UUID