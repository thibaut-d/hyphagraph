from pydantic import BaseModel, Field


class EntityCategoryRead(BaseModel):
    category_id: str
    label: dict[str, str]
    description: str
    examples: str | None
    is_active: bool
    is_system: bool
    usage_count: int


class EntityCategoryCreate(BaseModel):
    category_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=50)
    label: dict[str, str] = Field(..., description="i18n labels: {'en': 'Label'}")
    description: str = Field(..., min_length=10, max_length=500)
    examples: str | None = None


class EntityCategoryUpdate(BaseModel):
    label: dict[str, str] | None = None
    description: str | None = Field(None, min_length=10, max_length=500)
    examples: str | None = None
    is_active: bool | None = None


def entity_category_to_read(row) -> EntityCategoryRead:
    import json
    return EntityCategoryRead(
        category_id=row.category_id,
        label=json.loads(row.label) if isinstance(row.label, str) else row.label,
        description=row.description,
        examples=row.examples,
        is_active=row.is_active,
        is_system=row.is_system,
        usage_count=row.usage_count,
    )
