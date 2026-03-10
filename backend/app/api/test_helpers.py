"""
Test Helper API Endpoints

SECURITY WARNING: These endpoints are ONLY enabled when TESTING=True.
They provide dangerous operations like database truncation for E2E testing.

DO NOT enable these endpoints in production.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/test", tags=["test-helpers"])


def check_testing_mode():
    """
    Dependency to ensure test endpoints are only accessible in testing mode.

    Raises:
        HTTPException: 403 if not in testing mode
    """
    if not settings.TESTING:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test endpoints are only available when TESTING=True"
        )


@router.post("/reset-database", dependencies=[Depends(check_testing_mode)])
async def reset_database(db: AsyncSession = Depends(get_db)):
    """
    Reset the database by truncating all tables.

    DANGER: This deletes ALL data from the database!
    Only available when TESTING=True.

    This is used by E2E tests to ensure clean state between test runs.

    Returns:
        dict: Success message with number of tables truncated
    """
    try:
        # Get all table names from the database
        result = await db.execute(text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename NOT LIKE 'alembic%'
        """))
        tables = [row[0] for row in result.fetchall()]

        if not tables:
            return {"message": "No tables to truncate", "tables_truncated": 0}

        # Disable foreign key checks temporarily
        await db.execute(text("SET session_replication_role = 'replica';"))

        # Truncate all tables
        for table in tables:
            await db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))

        # Re-enable foreign key checks
        await db.execute(text("SET session_replication_role = 'origin';"))

        await db.commit()

        return {
            "message": f"Successfully truncated {len(tables)} tables",
            "tables_truncated": len(tables),
            "tables": tables
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset database: {str(e)}"
        )


@router.get("/health", dependencies=[Depends(check_testing_mode)])
async def test_health():
    """
    Health check endpoint for test helpers.

    Returns:
        dict: Status message confirming testing mode is enabled
    """
    return {
        "status": "ok",
        "testing_mode": settings.TESTING,
        "message": "Test helper endpoints are available"
    }
