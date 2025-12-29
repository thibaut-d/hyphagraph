"""
Entity term service for managing entity aliases and synonyms.

Provides CRUD operations for entity terms with proper error handling
and database transaction management.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List
from fastapi import HTTPException

from app.models.entity_term import EntityTerm
from app.models.entity import Entity
from app.schemas.entity_term import EntityTermWrite, EntityTermRead


class EntityTermService:
    """
    Service for managing entity terms (aliases/synonyms).

    Entity terms allow entities to have multiple names in different
    languages or contexts (e.g., "paracetamol", "acetaminophen", "Tylenol").
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_entity(self, entity_id: UUID) -> List[EntityTermRead]:
        """
        Get all terms for a specific entity.

        Returns terms ordered by:
        1. display_order (ascending, nulls last)
        2. created_at (descending)

        Args:
            entity_id: The entity UUID

        Returns:
            List of EntityTermRead objects
        """
        # Verify entity exists
        entity_stmt = select(Entity).where(Entity.id == entity_id)
        entity_result = await self.db.execute(entity_stmt)
        entity = entity_result.scalar_one_or_none()

        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        # Fetch terms
        stmt = (
            select(EntityTerm)
            .where(EntityTerm.entity_id == entity_id)
            .order_by(
                EntityTerm.display_order.asc().nulls_last(),
                EntityTerm.created_at.desc()
            )
        )

        result = await self.db.execute(stmt)
        terms = result.scalars().all()

        return [
            EntityTermRead(
                id=term.id,
                entity_id=term.entity_id,
                term=term.term,
                language=term.language,
                display_order=term.display_order,
                created_at=term.created_at,
            )
            for term in terms
        ]

    async def create(
        self, entity_id: UUID, payload: EntityTermWrite
    ) -> EntityTermRead:
        """
        Create a new term for an entity.

        Args:
            entity_id: The entity UUID
            payload: EntityTermWrite with term data

        Returns:
            EntityTermRead of the created term

        Raises:
            HTTPException: 404 if entity not found
            HTTPException: 409 if term already exists for entity+language
        """
        # Verify entity exists
        entity_stmt = select(Entity).where(Entity.id == entity_id)
        entity_result = await self.db.execute(entity_stmt)
        entity = entity_result.scalar_one_or_none()

        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        # Create term
        term = EntityTerm(
            entity_id=entity_id,
            term=payload.term,
            language=payload.language,
            display_order=payload.display_order,
        )

        self.db.add(term)

        try:
            await self.db.commit()
            await self.db.refresh(term)
        except IntegrityError as e:
            await self.db.rollback()
            # Unique constraint violation (entity_id, term, language)
            # PostgreSQL: "uq_entity_term_language", SQLite: "UNIQUE constraint failed: entity_terms"
            error_str = str(e).lower()
            if "uq_entity_term_language" in error_str or "entity_terms.entity_id, entity_terms.term, entity_terms.language" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail=f"Term '{payload.term}' already exists for this entity and language"
                )
            raise

        return EntityTermRead(
            id=term.id,
            entity_id=term.entity_id,
            term=term.term,
            language=term.language,
            display_order=term.display_order,
            created_at=term.created_at,
        )

    async def update(
        self, entity_id: UUID, term_id: UUID, payload: EntityTermWrite
    ) -> EntityTermRead:
        """
        Update an existing term.

        Args:
            entity_id: The entity UUID
            term_id: The term UUID to update
            payload: EntityTermWrite with updated data

        Returns:
            EntityTermRead of the updated term

        Raises:
            HTTPException: 404 if term not found or doesn't belong to entity
            HTTPException: 409 if updated term conflicts with existing
        """
        # Fetch term
        stmt = select(EntityTerm).where(
            EntityTerm.id == term_id,
            EntityTerm.entity_id == entity_id
        )
        result = await self.db.execute(stmt)
        term = result.scalar_one_or_none()

        if not term:
            raise HTTPException(
                status_code=404,
                detail="Term not found or does not belong to this entity"
            )

        # Update fields
        term.term = payload.term
        term.language = payload.language
        term.display_order = payload.display_order

        try:
            await self.db.commit()
            await self.db.refresh(term)
        except IntegrityError as e:
            await self.db.rollback()
            # PostgreSQL: "uq_entity_term_language", SQLite: "UNIQUE constraint failed: entity_terms"
            error_str = str(e).lower()
            if "uq_entity_term_language" in error_str or "entity_terms.entity_id, entity_terms.term, entity_terms.language" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail=f"Term '{payload.term}' already exists for this entity and language"
                )
            raise

        return EntityTermRead(
            id=term.id,
            entity_id=term.entity_id,
            term=term.term,
            language=term.language,
            display_order=term.display_order,
            created_at=term.created_at,
        )

    async def delete(self, entity_id: UUID, term_id: UUID) -> None:
        """
        Delete a term.

        Args:
            entity_id: The entity UUID
            term_id: The term UUID to delete

        Raises:
            HTTPException: 404 if term not found or doesn't belong to entity
        """
        # Verify term exists and belongs to entity
        stmt = select(EntityTerm).where(
            EntityTerm.id == term_id,
            EntityTerm.entity_id == entity_id
        )
        result = await self.db.execute(stmt)
        term = result.scalar_one_or_none()

        if not term:
            raise HTTPException(
                status_code=404,
                detail="Term not found or does not belong to this entity"
            )

        # Delete term
        await self.db.delete(term)
        await self.db.commit()

    async def bulk_update(
        self, entity_id: UUID, terms: List[EntityTermWrite]
    ) -> List[EntityTermRead]:
        """
        Replace all terms for an entity.

        Deletes all existing terms and creates new ones.
        This is transactional - if any term fails, all changes are rolled back.

        Args:
            entity_id: The entity UUID
            terms: List of new terms to create

        Returns:
            List of created EntityTermRead objects

        Raises:
            HTTPException: 404 if entity not found
            HTTPException: 409 if duplicate terms in payload
        """
        # Verify entity exists
        entity_stmt = select(Entity).where(Entity.id == entity_id)
        entity_result = await self.db.execute(entity_stmt)
        entity = entity_result.scalar_one_or_none()

        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")

        # Delete all existing terms
        delete_stmt = delete(EntityTerm).where(EntityTerm.entity_id == entity_id)
        await self.db.execute(delete_stmt)

        # Create new terms
        created_terms = []
        for term_data in terms:
            term = EntityTerm(
                entity_id=entity_id,
                term=term_data.term,
                language=term_data.language,
                display_order=term_data.display_order,
            )
            self.db.add(term)
            created_terms.append(term)

        try:
            await self.db.commit()

            # Refresh all terms to get generated IDs and timestamps
            for term in created_terms:
                await self.db.refresh(term)

        except IntegrityError as e:
            await self.db.rollback()
            # PostgreSQL: "uq_entity_term_language", SQLite: "UNIQUE constraint failed: entity_terms"
            error_str = str(e).lower()
            if "uq_entity_term_language" in error_str or "entity_terms.entity_id, entity_terms.term, entity_terms.language" in error_str:
                raise HTTPException(
                    status_code=409,
                    detail="Duplicate terms detected in payload"
                )
            raise

        # Return in sorted order
        created_terms.sort(
            key=lambda t: (
                t.display_order if t.display_order is not None else float('inf'),
                -t.created_at.timestamp()
            )
        )

        return [
            EntityTermRead(
                id=term.id,
                entity_id=term.entity_id,
                term=term.term,
                language=term.language,
                display_order=term.display_order,
                created_at=term.created_at,
            )
            for term in created_terms
        ]
