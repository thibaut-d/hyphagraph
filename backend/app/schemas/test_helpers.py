"""
Schemas for testing-only helper endpoints.

Only used when TESTING=True.
"""
from app.schemas.base import Schema


class DatabaseResetResponse(Schema):
    message: str
    tables_truncated: int
    tables: list[str] = []


class ReviewQueueSeedResponse(Schema):
    message: str
    source_id: str
    entity_id: str
    extractions_created: int


class UICategoriesSeedResponse(Schema):
    message: str
    count: int


class TestHealthResponse(Schema):
    __test__ = False

    status: str
    testing_mode: bool
    env: str
    email_from: str
    email_verification_required: bool
    message: str
