"""Repository for computed relation cache management."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sql_delete, select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.computed_relation import ComputedRelation
from app.models.relation import Relation
from app.models.relation_revision import RelationRevision
from app.models.relation_role_revision import RelationRoleRevision


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
        await self.db.execute(
            sql_delete(ComputedRelation).where(ComputedRelation.scope_hash == scope_hash)
        )

    async def delete_by_entity_id(self, entity_id: UUID) -> None:
        """
        Invalidate all cache entries whose stored roles reference the given entity.

        Joins through ComputedRelation → Relation → RelationRevision (is_current)
        → RelationRoleRevision to find every cached inference that was computed
        for this entity, then deletes those ComputedRelation rows.

        Call this whenever a source relation is created, updated, or deleted so
        that the entity's next inference request re-runs the math.
        """
        # Collect IDs to delete via a SELECT with joins, then bulk-delete.
        id_stmt = (
            select(ComputedRelation.relation_id)
            .join(Relation, ComputedRelation.relation_id == Relation.id)
            .join(
                RelationRevision,
                (RelationRevision.relation_id == Relation.id)
                & (RelationRevision.is_current == True),
            )
            .join(
                RelationRoleRevision,
                RelationRoleRevision.relation_revision_id == RelationRevision.id,
            )
            .where(RelationRoleRevision.entity_id == entity_id)
            .distinct()
        )
        result = await self.db.execute(id_stmt)
        ids = [row[0] for row in result.all()]
        if ids:
            await self.db.execute(
                sql_delete(ComputedRelation).where(ComputedRelation.relation_id.in_(ids))
            )

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
