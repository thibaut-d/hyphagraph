from pydantic import BaseModel, ConfigDict, Field


class TypeDBExportBundle(BaseModel):
    """Complete TypeDB export package."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_text: str = Field(alias="schema")
    data: str
    format: str
    database: str
    version: str
