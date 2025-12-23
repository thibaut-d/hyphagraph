from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.models.relation import Relation


class RelationRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, relation_id: UUID) -> Relation | None:
        stmt = select(Relation).where(Relation.id == relation_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, relation: Relation) -> Relation:
        self.db.add(relation)
        await self.db.flush()
        return relation