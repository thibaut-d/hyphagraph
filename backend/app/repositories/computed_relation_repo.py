"""Repository for computed relation cache management."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.computed_relation import ComputedRelation
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision


class ComputedRelationRepository:
    """Repository for computed relation cache operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_scope_hash(
        self,
        scope_hash: str,
        model_version: str
    ) -> ComputedRelation | None:
        """
        Look up cached computed relation by scope hash and model version.

        Args:
            scope_hash: Deterministic hash of query scope
            model_version: Version of inference model

        Returns:
            Cached ComputedRelation or None if not found or outdated
        """
        stmt = (
            select(ComputedRelation)
            .where(
                ComputedRelation.scope_hash == scope_hash,
                ComputedRelation.model_version == model_version
            )
            .options(
                selectinload(ComputedRelation.relation).selectinload(Relation.revisions).selectinload(RelationRevision.roles)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, computed_relation: ComputedRelation) -> ComputedRelation:
        """
        Store a new computed relation in cache.

        Args:
            computed_relation: ComputedRelation to cache

        Returns:
            The stored ComputedRelation
        """
        self.db.add(computed_relation)
        await self.db.flush()
        return computed_relation

    async def delete_by_scope_hash(self, scope_hash: str) -> None:
        """
        Invalidate cache entries for a specific scope hash.

        Args:
            scope_hash: Scope hash to invalidate
        """
        stmt = select(ComputedRelation).where(ComputedRelation.scope_hash == scope_hash)
        result = await self.db.execute(stmt)
        computed_relations = result.scalars().all()

        for cr in computed_relations:
            await self.db.delete(cr)

    async def delete_by_relation_id(self, relation_id: UUID) -> None:
        """
        Delete a computed relation by its relation ID.

        Args:
            relation_id: Relation ID of the computed relation
        """
        stmt = select(ComputedRelation).where(ComputedRelation.relation_id == relation_id)
        result = await self.db.execute(stmt)
        computed_relation = result.scalar_one_or_none()

        if computed_relation:
            await self.db.delete(computed_relation)
