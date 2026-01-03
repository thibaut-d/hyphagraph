from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


# -------------------------------------------------------------------
# Engine
# -------------------------------------------------------------------

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.SQL_DEBUG,
    pool_pre_ping=True,
    pool_size=20,  # Increased for E2E test load (default: 5)
    max_overflow=30,  # Increased overflow capacity (default: 10)
    pool_timeout=30,  # Connection acquisition timeout in seconds
    pool_recycle=3600,  # Recycle connections after 1 hour
)


# -------------------------------------------------------------------
# Session factory
# -------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


# -------------------------------------------------------------------
# FastAPI dependency
# -------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency.

    Provides an async SQLAlchemy session.
    Ensures proper cleanup.
    """
    async with AsyncSessionLocal() as session:
        yield session