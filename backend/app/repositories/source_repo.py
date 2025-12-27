from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.models.source import Source


class SourceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, source_id: UUID) -> Source | None:
        stmt = select(Source).where(Source.id == source_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Source]:
        stmt = select(Source).order_by(Source.year.desc(), Source.title)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, source: Source) -> Source:
        self.db.add(source)
        await self.db.flush()
        return source

    async def delete(self, source: Source) -> None:
        await self.db.delete(source)