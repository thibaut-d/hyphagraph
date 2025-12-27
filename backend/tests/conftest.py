"""
Pytest configuration and shared fixtures.

Uses SQLite for testing to avoid PostgreSQL dependency.
Monkey-patches PostgreSQL ARRAY to work with SQLite.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import TypeDecorator, Text, event, text as sql_text
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import String
import json
import sqlalchemy

# Monkey-patch ARRAY and JSONB to use JSON in SQLite BEFORE importing models
original_array = postgresql.ARRAY
original_jsonb = postgresql.JSONB

class SQLiteCompatibleArray(TypeDecorator):
    """Makes PostgreSQL ARRAY work with SQLite by storing as JSON."""
    impl = Text
    cache_ok = True

    def __init__(self, item_type=None):
        super().__init__()
        self.item_type = item_type

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if dialect.name == "sqlite":
            return json.loads(value) if value else []
        return value

class SQLiteCompatibleJSONB(TypeDecorator):
    """Makes PostgreSQL JSONB work with SQLite by using JSON."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            return json.loads(value) if value else None
        return value

# Replace ARRAY and JSONB in both locations before models are imported
postgresql.ARRAY = SQLiteCompatibleArray
sqlalchemy.ARRAY = SQLiteCompatibleArray
postgresql.JSONB = SQLiteCompatibleJSONB

from app.models.base import Base
from app.config import settings

# Import all models AFTER monkey-patching
from app.models.user import User  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.entity import Entity  # noqa: F401
from app.models.entity_revision import EntityRevision  # noqa: F401
from app.models.entity_term import EntityTerm  # noqa: F401
from app.models.ui_category import UiCategory  # noqa: F401
from app.models.source import Source  # noqa: F401
from app.models.source_revision import SourceRevision  # noqa: F401
from app.models.relation import Relation  # noqa: F401
from app.models.relation_revision import RelationRevision  # noqa: F401
from app.models.relation_role_revision import RelationRoleRevision  # noqa: F401

# Use SQLite for testing (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Enable foreign keys in SQLite
@event.listens_for(Base.metadata, "before_create")
def _set_sqlite_pragma(target, connection, **kw):
    """Enable foreign keys in SQLite."""
    if connection.dialect.name == "sqlite":
        connection.execute(sql_text("PRAGMA foreign_keys=ON"))


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """
    Provide a transactional database session for tests.

    Uses SQLite in-memory database for fast, isolated tests.
    Creates tables before test, rolls back after test.
    """
    # Create SQLite in-memory engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,  # Required for in-memory SQLite
        connect_args={"check_same_thread": False},  # Allow multi-threaded access
    )

    # Enable foreign keys and create all tables
    async with engine.begin() as conn:
        await conn.execute(sql_text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    # Provide session for test
    async with async_session() as session:
        yield session
        await session.rollback()  # Rollback any uncommitted changes

    # Cleanup
    await engine.dispose()
