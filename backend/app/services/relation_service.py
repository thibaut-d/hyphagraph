from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.schemas.relation import RelationWrite, RelationRead
from app.repositories.relation_repo import RelationRepository
from app.mappers.relation_mapper import (
    relation_from_write,
    relation_to_read,
)
from app.services.validation_service import validate_relation


class RelationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = RelationRepository(db)

    async def create(self, payload: RelationWrite) -> RelationRead:
        """
        Create a relation (hyper-edge).
        """
        # 1. Structural validation
        validate_relation(payload)

        try:
            # 2. Map Write → ORM
            relation = relation_from_write(payload)

            # 3. Persist
            await self.repo.create(relation)

            # 4. Commit transaction
            await self.db.commit()

            # 5. Return Read
            return relation_to_read(relation)

        except Exception:
            await self.db.rollback()
            raise

    async def get(self, relation_id) -> RelationRead:
        relation = await self.repo.get_by_id(relation_id)
        if not relation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relation not found",
            )
        return relation_to_read(relation)