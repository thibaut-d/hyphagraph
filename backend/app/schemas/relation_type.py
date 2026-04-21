import json

from pydantic import BaseModel, Field

from app.models.relation_type import RelationType


class RelationTypeRead(BaseModel):
    """Read schema for relation type."""

    type_id: str
    label: dict[str, str]
    description: str
    examples: str | None
    aliases: list[str] | None
    category: str | None
    usage_count: int
    is_system: bool


class RelationTypeCreate(BaseModel):
    """Create schema for relation type."""

    type_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=50)
    label: dict[str, str] = Field(..., description="i18n labels: {'en': 'Label', 'fr': 'Libellé'}")
    description: str = Field(..., min_length=10, max_length=500)
    examples: str | None = None
    aliases: list[str] | None = None
    category: str | None = Field(None, description="therapeutic, causal, diagnostic, etc.")


class RelationTypeUpdate(BaseModel):
    """Update schema for relation type (all fields optional)."""

    label: dict[str, str] | None = None
    description: str | None = Field(None, min_length=10, max_length=500)
    examples: str | None = None
    aliases: list[str] | None = None
    category: str | None = None
    is_active: bool | None = None


class SuggestNewTypeRequest(BaseModel):
    """Request to check if a new relation type should be added."""

    proposed_type: str
    context: str = Field(..., description="Description or use case for this type")


class SuggestNewTypeResponse(BaseModel):
    """Response describing whether a new relation type should be added."""

    similar_existing: str | None
    should_add: bool
    reason: str


class RelationTypeStatisticsRead(BaseModel):
    """Relation type usage statistics."""

    total_types: int
    system_types: int
    user_types: int
    total_usage: int
    by_category: dict[str, int]
    most_used: list[RelationTypeRead]


class RelationTypePromptRead(BaseModel):
    """Response schema for prompt-formatted relation type output."""

    prompt_text: str


def relation_type_to_read(relation_type: RelationType) -> RelationTypeRead:
    """Convert a relation type ORM row into the API read schema."""

    return RelationTypeRead(
        type_id=relation_type.type_id,
        label=json.loads(relation_type.label) if isinstance(relation_type.label, str) else relation_type.label,
        description=relation_type.description,
        examples=relation_type.examples,
        aliases=(
            json.loads(relation_type.aliases)
            if relation_type.aliases and isinstance(relation_type.aliases, str)
            else (relation_type.aliases if relation_type.aliases else None)
        ),
        category=relation_type.category,
        usage_count=relation_type.usage_count,
        is_system=relation_type.is_system,
    )
