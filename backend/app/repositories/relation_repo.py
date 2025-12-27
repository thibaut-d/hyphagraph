from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision


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

    async def list_by_source(self, source_id: UUID) -> list[Relation]:
        stmt = (
            select(Relation)
            .where(Relation.source_id == source_id)
            .options(
                selectinload(Relation.revisions).selectinload(RelationRevision.roles)
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_entity(self, entity_id: UUID) -> list[Relation]:
        """Find all relations involving an entity via RelationRoleRevision."""
        # Get relation IDs via RelationRoleRevision
        stmt_ids = (
            select(Relation.id)
            .join(RelationRevision)
            .join(RelationRoleRevision)
            .where(RelationRoleRevision.entity_id == entity_id)
        )
        result = await self.db.execute(stmt_ids)
        relation_ids = [row[0] for row in result.all()]

        if not relation_ids:
            return []

        # Fetch full relations with eager loading
        stmt = (
            select(Relation)
            .where(Relation.id.in_(relation_ids))
            .options(
                selectinload(Relation.revisions).selectinload(RelationRevision.roles)
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def delete(self, relation: Relation) -> None:
        await self.db.delete(relation)