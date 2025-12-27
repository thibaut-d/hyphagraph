from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.models.entity import Entity


class EntityRepository:
    """
    Database access layer for Entity.

    - No business logic
    - No validation
    - No Pydantic
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, entity_id: UUID) -> Entity | None:
        stmt = select(Entity).where(Entity.id == entity_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Entity]:
        stmt = select(Entity).order_by(Entity.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, entity: Entity) -> Entity:
        self.db.add(entity)
        await self.db.flush()  # assign PK without committing
        return entity

    async def delete(self, entity: Entity) -> None:
        await self.db.delete(entity)