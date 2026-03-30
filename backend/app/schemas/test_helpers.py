"""
Response schemas for test helper endpoints.

Only used when TESTING=True.
"""
from pydantic import BaseModel


class DatabaseResetResponse(BaseModel):
    message: str
    tables_truncated: int
    tables: list[str]


class ReviewQueueSeedResponse(BaseModel):
    message: str
    source_id: str
    entity_id: str
    extractions_created: int


class UICategoriesSeedResponse(BaseModel):
    message: str
    count: int


class TestHealthResponse(BaseModel):
    status: str
    testing_mode: bool
    message: str
