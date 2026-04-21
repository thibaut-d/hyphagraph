"""
Relation Type Service - Manage dynamic relation type vocabulary.

Provides:
- CRUD operations for relation types
- Similarity detection (avoid duplicates)
- LLM prompt generation with current types
- Usage tracking
- Suggestion system for new types
"""
from datetime import datetime, timezone
import difflib
import logging
from typing import List

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.relation_type import RelationType
from app.models.staged_extraction import ExtractionStatus, ExtractionType
from app.schemas.relation_type import RelationTypeStatisticsRead, SuggestNewTypeResponse, relation_type_to_read

logger = logging.getLogger(__name__)


class RelationTypeService:
    """Service for managing relation type vocabulary."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> List[RelationType]:
        """Get all active relation types."""
        stmt = select(RelationType).where(
            RelationType.is_active == True
        ).order_by(RelationType.usage_count.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, type_id: str) -> RelationType | None:
        """Get relation type by ID."""
        stmt = select(RelationType).where(RelationType.type_id == type_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_relation_type(
        self,
        type_id: str,
        label: dict,
        description: str,
        examples: str | None = None,
        aliases: list[str] | None = None,
        category: str | None = None,
        is_system: bool = False
    ) -> RelationType:
        """
        Create a new relation type.

        Before creating, checks for similar existing types to avoid duplicates.
        """
        # Check if already exists
        existing = await self.get_by_id(type_id)
        if existing:
            raise ValueError(f"Relation type '{type_id}' already exists")

        # Check for similar types (prevent duplicates)
        similar = await self.find_similar(type_id, description)
        if similar:
            raise ValueError(
                f"Similar relation type already exists: '{similar.type_id}'. "
                f"Consider using that instead or adding '{type_id}' as an alias."
            )

        # Create new type
        new_type = RelationType(
            type_id=type_id,
            label=label,
            description=description,
            examples=examples,
            aliases=aliases,
            is_active=True,
            is_system=is_system,
            usage_count=0,
            category=category,
            created_at=datetime.now(timezone.utc)
        )

        self.db.add(new_type)
        await self.db.commit()
        await self.db.refresh(new_type)

        return new_type

    async def update_relation_type(
        self,
        type_id: str,
        label: dict | None = None,
        description: str | None = None,
        examples: str | None = None,
        aliases: list[str] | None = None,
        category: str | None = None,
        is_active: bool | None = None,
    ) -> RelationType | None:
        """Update an existing relation type. Only provided fields are changed."""
        relation_type = await self.get_by_id(type_id)
        if relation_type is None:
            return None

        if label is not None:
            relation_type.label = label
        if description is not None:
            relation_type.description = description
        if examples is not None:
            relation_type.examples = examples
        if aliases is not None:
            relation_type.aliases = aliases
        if category is not None:
            relation_type.category = category
        if is_active is not None:
            relation_type.is_active = is_active

        await self.db.commit()
        await self.db.refresh(relation_type)
        return relation_type

    async def delete_relation_type(self, type_id: str) -> bool:
        """
        Delete a relation type by ID.

        System types are soft-deleted (is_active=False). User-created types
        are hard-deleted.
        """
        relation_type = await self.get_by_id(type_id)
        if relation_type is None:
            return False

        if relation_type.is_system:
            # Soft-delete system types
            relation_type.is_active = False
            await self.db.commit()
        else:
            await self.db.delete(relation_type)
            await self.db.commit()

        return True

    async def count_pending_staged_by_relation_type(self, type_id: str) -> int:
        """
        Count pending staged relation extractions that use the given relation type.

        Used to populate the merge confirmation dialog.
        """
        result = await self.db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM staged_extractions
                WHERE extraction_type = :etype
                  AND status = :status
                  AND extraction_data->>'relation_type' = :type_id
                """
            ),
            {
                "etype": ExtractionType.RELATION.value,
                "status": ExtractionStatus.PENDING.value,
                "type_id": type_id,
            },
        )
        return result.scalar_one()

    async def count_revisions_by_relation_type(self, type_id: str) -> int:
        """
        Count materialized relation revisions that use the given relation type.

        Used to populate the merge confirmation dialog.
        """
        result = await self.db.execute(
            text("SELECT COUNT(*) FROM relation_revisions WHERE kind = :type_id"),
            {"type_id": type_id},
        )
        return result.scalar_one()

    async def merge_relation_types(
        self,
        source_id: str,
        target_id: str,
    ) -> dict:
        """
        Merge source relation type into target relation type.

        - Re-labels all relation_revisions rows from source to target (kind column).
        - Re-labels all pending staged relation extractions (extraction_data->>'relation_type').
        - Soft-deletes the source type.
        - Commits atomically.

        Returns a summary dict: { updated_revisions, updated_staged, deactivated_type }.

        Raises ValueError for invalid merge requests.
        """
        if source_id == target_id:
            raise ValueError("source and target relation type must differ")

        source = await self.get_by_id(source_id)
        if source is None:
            raise ValueError(f"Source relation type '{source_id}' not found")

        target = await self.get_by_id(target_id)
        if target is None:
            raise ValueError(f"Target relation type '{target_id}' not found")

        if source.is_system and not target.is_system:
            raise ValueError(
                "Cannot merge a system relation type into a user-created type"
            )

        # Re-label all materialized relation revisions
        rev_result = await self.db.execute(
            text(
                "UPDATE relation_revisions SET kind = :target_id WHERE kind = :source_id"
            ),
            {"target_id": target_id, "source_id": source_id},
        )
        updated_revisions = rev_result.rowcount

        # Re-label pending staged relation extractions
        staged_result = await self.db.execute(
            text(
                """
                UPDATE staged_extractions
                SET extraction_data = jsonb_set(
                    extraction_data,
                    '{relation_type}',
                    :target_json
                )
                WHERE extraction_type = :etype
                  AND status = :status
                  AND extraction_data->>'relation_type' = :source_id
                """
            ),
            {
                "target_json": f'"{target_id}"',
                "etype": ExtractionType.RELATION.value,
                "status": ExtractionStatus.PENDING.value,
                "source_id": source_id,
            },
        )
        updated_staged = staged_result.rowcount

        # Soft-delete source type
        source.is_active = False
        await self.db.commit()

        logger.info(
            "Merged relation type '%s' → '%s': %d revisions, %d staged updated",
            source_id,
            target_id,
            updated_revisions,
            updated_staged,
        )
        return {
            "updated_revisions": updated_revisions,
            "updated_staged": updated_staged,
            "deactivated_type": source_id,
        }

    async def find_similar(
        self,
        type_id: str,
        description: str,
        similarity_threshold: float = 0.6
    ) -> RelationType | None:
        """
        Find similar relation type to avoid duplicates.

        Uses string similarity on type_id and description.
        """
        all_types = await self.get_all_active()

        for existing_type in all_types:
            # Check type_id similarity
            id_similarity = difflib.SequenceMatcher(
                None, type_id.lower(), existing_type.type_id.lower()
            ).ratio()

            if id_similarity >= similarity_threshold:
                return existing_type

            # Check if type_id matches any alias
            aliases = existing_type.aliases or []
            if type_id.lower() in [a.lower() for a in aliases]:
                return existing_type

            # Check description similarity
            desc_similarity = difflib.SequenceMatcher(
                None, description.lower(), existing_type.description.lower()
            ).ratio()

            if desc_similarity >= 0.8:  # Higher threshold for description
                return existing_type

        return None

    async def increment_usage(self, type_id: str) -> None:
        """Increment usage count for a relation type."""
        relation_type = await self.get_by_id(type_id)
        if relation_type:
            relation_type.usage_count += 1
            try:
                await self.db.commit()
            except Exception:
                logger.warning("Failed to increment usage count for relation type %s", type_id)
                await self.db.rollback()

    async def get_for_llm_prompt(self) -> str:
        """
        Generate formatted relation type list for LLM prompts.

        Returns a string formatted for inclusion in LLM prompts.
        """
        types = await self.get_all_active()

        prompt_lines = [
            "CRITICAL: relation_type MUST be EXACTLY one of these values (no variations):"
        ]

        for rt in types:
            # Format: - type_id: description
            prompt_lines.append(f"   - {rt.type_id}: {rt.description}")

            if rt.examples:
                prompt_lines.append(f"     Examples: {rt.examples}")

        prompt_lines.append("")
        prompt_lines.append(
            "   IMPORTANT: If the relationship doesn't clearly fit one of the specific types above, use 'other'."
        )
        prompt_lines.append(
            "   Do NOT invent new relation types. If you find a relationship that doesn't fit, "
            "note it for review and use 'other' for now."
        )

        return "\n".join(prompt_lines)

    async def suggest_new_type(
        self,
        proposed_type: str,
        context: str
    ) -> SuggestNewTypeResponse:
        """
        Suggest whether a new relation type should be added.

        Returns:
        - similar_existing: Existing type that's similar (or None)
        - should_add: Boolean recommendation
        - reason: Explanation
        """
        similar = await self.find_similar(proposed_type, context)

        if similar:
            return SuggestNewTypeResponse(
                similar_existing=similar.type_id,
                should_add=False,
                reason=(
                    f"Similar type '{similar.type_id}' already exists. Consider using it "
                    f"or adding '{proposed_type}' as an alias."
                ),
            )

        return SuggestNewTypeResponse(
            similar_existing=None,
            should_add=True,
            reason=f"No similar type found. '{proposed_type}' can be added as a new relation type.",
        )

    async def get_statistics(self) -> RelationTypeStatisticsRead:
        """Get relation type usage statistics."""
        all_types = await self.get_all_active()

        total_types = len(all_types)
        system_types = len([t for t in all_types if t.is_system])
        user_types = len([t for t in all_types if not t.is_system])
        total_usage = sum(t.usage_count for t in all_types)

        # Get by category
        categories = {}
        for t in all_types:
            cat = t.category or 'uncategorized'
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        most_used = sorted(all_types, key=lambda relation_type: relation_type.usage_count, reverse=True)[:10]

        return RelationTypeStatisticsRead(
            total_types=total_types,
            system_types=system_types,
            user_types=user_types,
            total_usage=total_usage,
            by_category=categories,
            most_used=[relation_type_to_read(relation_type) for relation_type in most_used],
        )
