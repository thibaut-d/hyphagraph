from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.entity import EntityWrite, EntityRead
from app.repositories.entity_repo import EntityRepository
from app.mappers.entity_mapper import (
    entity_from_write,
    entity_to_read,
)


class EntityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = EntityRepository(db)

    async def create(self, payload: EntityWrite) -> EntityRead:
        try:
            entity = entity_from_write(payload)
            await self.repo.create(entity)
            await self.db.commit()
            return entity_to_read(entity)
        except Exception:
            await self.db.rollback()
            raise

    async def get(self, entity_id) -> EntityRead:
        entity = await self.repo.get_by_id(entity_id)
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entity not found",
            )
        return entity_to_read(entity)