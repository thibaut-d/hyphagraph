from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.inference_cache import InferenceCache


class InferenceRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_scope_hash(self, scope_hash: str) -> InferenceCache | None:
        stmt = select(InferenceCache).where(
            InferenceCache.scope_hash == scope_hash
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()