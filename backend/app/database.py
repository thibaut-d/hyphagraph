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