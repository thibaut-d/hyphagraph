"""
Helper utilities for managing revisions.

Provides common patterns for:
- Getting current revision
- Creating new revisions
- Managing is_current flags
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import TypeVar, Type, Generic

# Generic type for revision models
TRevision = TypeVar('TRevision')


async def get_current_revision(
    db: AsyncSession,
    revision_class: Type[TRevision],
    parent_id_field: str,
    parent_id: UUID,
    load_relationships: list[str] | None = None,
) -> TRevision | None:
    """
    Get the current revision for a given parent entity.

    Args:
        db: Database session
        revision_class: The revision model class (e.g., EntityRevision)
        parent_id_field: Name of the FK field (e.g., 'entity_id')
        parent_id: UUID of the parent entity
        load_relationships: Optional list of relationship names to eager load

    Returns:
        Current revision or None if not found
    """
    from sqlalchemy.orm import selectinload

    stmt = (
        select(revision_class)
        .where(
            getattr(revision_class, parent_id_field) == parent_id,
            revision_class.is_current == True,  # noqa: E712
        )
    )

    # Add eager loading for specified relationships
    if load_relationships:
        for rel_name in load_relationships:
            stmt = stmt.options(selectinload(getattr(revision_class, rel_name)))

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_new_revision(
    db: AsyncSession,
    revision_class: Type[TRevision],
    parent_id_field: str,
    parent_id: UUID,
    revision_data: dict,
    set_as_current: bool = True,
) -> TRevision:
    """
    Create a new revision for a parent entity.

    If set_as_current=True, marks all other revisions as not current.

    Args:
        db: Database session
        revision_class: The revision model class
        parent_id_field: Name of the FK field
        parent_id: UUID of the parent entity
        revision_data: Data for the new revision
        set_as_current: Whether to mark this as the current revision

    Returns:
        The newly created revision
    """
    # Mark all existing revisions as not current
    if set_as_current:
        await db.execute(
            update(revision_class)
            .where(getattr(revision_class, parent_id_field) == parent_id)
            .values(is_current=False)
        )

    # Create new revision
    revision_data[parent_id_field] = parent_id
    revision_data['is_current'] = set_as_current

    revision = revision_class(**revision_data)
    db.add(revision)
    await db.flush()

    return revision


async def get_revision_history(
    db: AsyncSession,
    revision_class: Type[TRevision],
    parent_id_field: str,
    parent_id: UUID,
    limit: int | None = None,
) -> list[TRevision]:
    """
    Get all revisions for a parent entity, ordered by creation date (newest first).

    Args:
        db: Database session
        revision_class: The revision model class
        parent_id_field: Name of the FK field
        parent_id: UUID of the parent entity
        limit: Optional limit on number of revisions to return

    Returns:
        List of revisions, newest first
    """
    stmt = (
        select(revision_class)
        .where(getattr(revision_class, parent_id_field) == parent_id)
        .order_by(revision_class.created_at.desc())
    )

    if limit:
        stmt = stmt.limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())
