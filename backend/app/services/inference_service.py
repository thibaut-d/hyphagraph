from collections import defaultdict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.relation_repo import RelationRepository
from app.mappers.relation_mapper import relation_to_read
from app.schemas.inference import InferenceRead


class InferenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RelationRepository(db)

    async def infer_for_entity(self, entity_id: UUID) -> InferenceRead:
        relations = await self.repo.list_by_entity(entity_id)

        grouped = defaultdict(list)
        for rel in relations:
            grouped[rel.kind].append(relation_to_read(rel))

        return InferenceRead(
            entity_id=entity_id,
            relations_by_kind=dict(grouped),
        )