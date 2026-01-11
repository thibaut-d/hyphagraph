"""
Relation Type Service - Manage dynamic relation type vocabulary.

Provides:
- CRUD operations for relation types
- Similarity detection (avoid duplicates)
- LLM prompt generation with current types
- Usage tracking
- Suggestion system for new types
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import difflib

from app.models.relation_type import RelationType


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
        import json
        from datetime import datetime

        new_type = RelationType(
            type_id=type_id,
            label=label,
            description=description,
            examples=examples,
            aliases=json.dumps(aliases) if aliases else None,
            is_active=True,
            is_system=is_system,
            usage_count=0,
            category=category,
            created_at=datetime.utcnow()
        )

        self.db.add(new_type)
        await self.db.commit()
        await self.db.refresh(new_type)

        return new_type

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
            import json
            aliases = json.loads(existing_type.aliases) if existing_type.aliases else []
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
            await self.db.commit()

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
    ) -> dict:
        """
        Suggest whether a new relation type should be added.

        Returns:
        - similar_existing: Existing type that's similar (or None)
        - should_add: Boolean recommendation
        - reason: Explanation
        """
        similar = await self.find_similar(proposed_type, context)

        if similar:
            return {
                'similar_existing': similar.type_id,
                'should_add': False,
                'reason': f"Similar type '{similar.type_id}' already exists. Consider using it or adding '{proposed_type}' as an alias."
            }

        return {
            'similar_existing': None,
            'should_add': True,
            'reason': f"No similar type found. '{proposed_type}' can be added as a new relation type."
        }

    async def get_statistics(self) -> dict:
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

        return {
            'total_types': total_types,
            'system_types': system_types,
            'user_types': user_types,
            'total_usage': total_usage,
            'by_category': categories,
            'most_used': sorted(all_types, key=lambda t: t.usage_count, reverse=True)[:10]
        }
