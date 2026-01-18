"""
Semantic Role Service - Manage semantic role types vocabulary.

Provides:
- CRUD operations for semantic role types
- Prompt generation for LLM
- Validation and suggestions
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import json as json_module


class SemanticRoleService:
    """Service for managing semantic role types vocabulary."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> list[dict]:
        """Get all active semantic role types."""
        stmt = text("""
            SELECT role_type, label::text, description, category, examples
            FROM semantic_role_types
            WHERE is_active = true
            ORDER BY category, role_type
        """)

        result = await self.db.execute(stmt)
        roles = []

        for row in result:
            # Parse label JSON safely
            label = row[1]
            if isinstance(label, str):
                try:
                    label = json_module.loads(label)
                except json_module.JSONDecodeError:
                    # If parsing fails, use the raw string
                    label = {'en': label}

            roles.append({
                'role_type': row[0],
                'label': label,
                'description': row[2],
                'category': row[3],
                'examples': row[4]
            })

        return roles

    async def get_for_llm_prompt(self) -> str:
        """
        Generate formatted semantic role list for LLM prompts.

        Returns a string formatted for inclusion in LLM prompts.
        """
        roles = await self.get_all_active()

        prompt_lines = [
            "SEMANTIC ROLES (use these to specify how each entity participates):"
        ]

        # Group by category
        categories = {}
        for role in roles:
            cat = role['category'] or 'other'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(role)

        # Format by category
        for category, cat_roles in categories.items():
            prompt_lines.append(f"\n{category.upper()} ROLES:")
            for role in cat_roles:
                prompt_lines.append(f"   - {role['role_type']}: {role['description']}")
                if role['examples']:
                    prompt_lines.append(f"     Example: {role['examples']}")

        prompt_lines.append("")
        prompt_lines.append(
            "IMPORTANT: Each entity in a relation MUST have a semantic role. "
            "Use the most appropriate role from the list above."
        )

        return "\n".join(prompt_lines)

    async def create_role_type(
        self,
        role_type: str,
        label: dict,
        description: str,
        category: str = None,
        examples: str = None
    ) -> dict:
        """
        Create a new semantic role type.

        Args:
            role_type: Unique identifier (e.g., "agent")
            label: i18n labels {"en": "Agent", "fr": "Agent"}
            description: Description for LLM guidance
            category: Category (core, measurement, contextual)
            examples: Usage examples

        Returns:
            Created role type dict
        """
        stmt = text("""
            INSERT INTO semantic_role_types
            (role_type, label, description, category, examples, is_active, is_system)
            VALUES (:role_type, :label, :description, :category, :examples, true, false)
            RETURNING role_type, label, description, category, examples
        """)

        result = await self.db.execute(stmt, {
            'role_type': role_type,
            'label': json_module.dumps(label),
            'description': description,
            'category': category,
            'examples': examples
        })

        await self.db.commit()

        row = result.first()
        return {
            'role_type': row[0],
            'label': json_module.loads(row[1]) if isinstance(row[1], str) else row[1],
            'description': row[2],
            'category': row[3],
            'examples': row[4]
        }
