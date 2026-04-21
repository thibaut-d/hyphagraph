"""
EntityCategory Service - Manage entity category vocabulary.

Provides CRUD operations for entity categories, mirroring RelationTypeService.
"""
import logging
from typing import List

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity_category import EntityCategory
from app.models.staged_extraction import ExtractionStatus, ExtractionType

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

    async def get_for_llm_prompt(self) -> str:
        """
        Generate a formatted entity category list for injection into LLM prompts.

        Returns a string ready to be dropped into {entity_categories} template slots.
        """
        categories = await self.get_all_active()

        lines = ["CRITICAL: category MUST be EXACTLY one of these values (no others allowed):"]
        for cat in categories:
            label = cat.label.get("en", cat.category_id) if isinstance(cat.label, dict) else cat.category_id
            lines.append(f"   - {cat.category_id}: {cat.description}")
            if cat.examples:
                lines.append(f"     Examples: {cat.examples}")
        lines.append("")
        lines.append("   IMPORTANT: Do NOT invent new category names. If an entity does not fit any listed")
        lines.append("   category, use 'other'.")
        return "\n".join(lines)

    async def count_pending_staged_by_category(self, category_id: str) -> int:
        """
        Count pending staged entity extractions that use the given category.

        Used to populate the merge confirmation dialog.
        """
        result = await self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM staged_extractions
                WHERE extraction_type = :etype
                  AND status = :status
                  AND extraction_data->>'category' = :category_id
                """
            ),
            {
                "etype": ExtractionType.ENTITY.value,
                "status": ExtractionStatus.PENDING.value,
                "category_id": category_id,
            },
        )
        return result.scalar_one()

    async def merge_entity_categories(
        self,
        source_id: str,
        target_id: str,
    ) -> dict:
        """
        Merge source category into target category.

        - Re-labels all pending staged entity extractions from source to target.
        - Soft-deletes the source category.
        - Commits atomically.

        Returns a summary dict: { updated_staged, deactivated_category }.

        Raises ValueError for invalid merge requests (same IDs, system→non-system, not found).
        """
        if source_id == target_id:
            raise ValueError("source and target category must differ")

        source = await self.get_by_id(source_id)
        if source is None:
            raise ValueError(f"Source category '{source_id}' not found")

        target = await self.get_by_id(target_id)
        if target is None:
            raise ValueError(f"Target category '{target_id}' not found")

        if source.is_system and not target.is_system:
            raise ValueError(
                "Cannot merge a system category into a user-created category"
            )

        # Re-label pending staged entity extractions
        result = await self.db.execute(
            text(
                """
                UPDATE staged_extractions
                SET extraction_data = jsonb_set(
                    extraction_data,
                    '{category}',
                    :target_json
                )
                WHERE extraction_type = :etype
                  AND status = :status
                  AND extraction_data->>'category' = :source_id
                """
            ),
            {
                "target_json": f'"{target_id}"',
                "etype": ExtractionType.ENTITY.value,
                "status": ExtractionStatus.PENDING.value,
                "source_id": source_id,
            },
        )
        updated_staged = result.rowcount

        # Soft-delete source category
        source.is_active = False
        await self.db.commit()

        logger.info(
            "Merged entity category '%s' → '%s': %d staged extractions updated",
            source_id,
            target_id,
            updated_staged,
        )
        return {
            "updated_staged": updated_staged,
            "deactivated_category": source_id,
        }

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
