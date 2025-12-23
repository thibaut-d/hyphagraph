from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.source import SourceWrite, SourceRead
from app.repositories.source_repo import SourceRepository
from app.mappers.source_mapper import (
    source_from_write,
    source_to_read,
)


class SourceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = SourceRepository(db)

    async def create(self, payload: SourceWrite) -> SourceRead:
        try:
            source = source_from_write(payload)
            await self.repo.create(source)
            await self.db.commit()
            return source_to_read(source)
        except Exception:
            await self.db.rollback()
            raise

    async def get(self, source_id) -> SourceRead:
        source = await self.repo.get_by_id(source_id)
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found",
            )
        return source_to_read(source)