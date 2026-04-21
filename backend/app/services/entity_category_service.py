"""
EntityCategory Service - Manage entity category vocabulary.

Provides CRUD operations for entity categories, mirroring RelationTypeService.
"""
import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity_category import EntityCategory

logger = logging.getLogger(__name__)


class EntityCategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> List[EntityCategory]:
        stmt = select(EntityCategory).where(EntityCategory.is_active == True).order_by(
            EntityCategory.usage_count.desc()
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self) -> List[EntityCategory]:
        """Return all categories including inactive ones (admin use)."""
        result = await self.db.execute(select(EntityCategory).order_by(EntityCategory.usage_count.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, category_id: str) -> EntityCategory | None:
        stmt = select(EntityCategory).where(EntityCategory.category_id == category_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        category_id: str,
        label: dict,
        description: str,
        examples: str | None = None,
    ) -> EntityCategory:
        existing = await self.get_by_id(category_id)
        if existing:
            raise ValueError(f"Entity category '{category_id}' already exists")

        row = EntityCategory(
            category_id=category_id,
            label=label,
            description=description,
            examples=examples,
            is_active=True,
            is_system=False,
            usage_count=0,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update(
        self,
        category_id: str,
        label: dict | None = None,
        description: str | None = None,
        examples: str | None = None,
        is_active: bool | None = None,
    ) -> EntityCategory | None:
        row = await self.get_by_id(category_id)
        if row is None:
            return None

        if label is not None:
            row.label = label
        if description is not None:
            row.description = description
        if examples is not None:
            row.examples = examples
        if is_active is not None:
            row.is_active = is_active

        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete(self, category_id: str) -> bool:
        row = await self.get_by_id(category_id)
        if row is None:
            return False

        if row.is_system:
            row.is_active = False
            await self.db.commit()
        else:
            await self.db.delete(row)
            await self.db.commit()

        return True
