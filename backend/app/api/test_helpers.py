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
from app.schemas.test_helpers import (
    DatabaseResetResponse,
    ReviewQueueSeedResponse,
    TestHealthResponse,
    UICategoriesSeedResponse,
)
from app.startup import run_bootstrap_tasks

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


@router.post("/reset-database", response_model=DatabaseResetResponse, dependencies=[Depends(check_testing_mode)])
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

        # Restore baseline bootstrap data so E2E can immediately authenticate
        # and rely on system-owned records after a reset.
        await run_bootstrap_tasks(db)

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


@router.post("/seed-review-queue", response_model=ReviewQueueSeedResponse, dependencies=[Depends(check_testing_mode)])
async def seed_review_queue(db: AsyncSession = Depends(get_db)):
    """
    Seed the review queue with staged extraction records for E2E testing.

    Creates a source, an entity, and pending staged extractions so that
    review queue tests can exercise the approve/reject/select-all UI paths.

    Only available when TESTING=True.
    """
    from datetime import datetime, timezone
    from app.models.source import Source
    from app.models.source_revision import SourceRevision
    from app.models.entity import Entity
    from app.models.entity_revision import EntityRevision
    from app.models.staged_extraction import StagedExtraction

    try:
        # --- Source ---
        source = Source()
        db.add(source)
        await db.flush()

        source_rev = SourceRevision(
            source_id=source.id,
            kind="study",
            title="E2E Seed Source",
            url="https://example.com/seed-source",
            status="confirmed",
            is_current=True,
        )
        db.add(source_rev)

        # --- Entity (needed for materialized_entity_id link) ---
        entity = Entity()
        db.add(entity)
        await db.flush()

        entity_rev = EntityRevision(
            entity_id=entity.id,
            slug=f"seed-entity-{str(entity.id)[:8]}",
            status="confirmed",
            is_current=True,
        )
        db.add(entity_rev)

        # --- Staged Extractions ---
        extractions = [
            StagedExtraction(
                extraction_type="entity",
                status="pending",
                source_id=source.id,
                extraction_data={"slug": "aspirin", "summary": {"en": "A common painkiller"}},
                validation_score=0.85,
                materialized_entity_id=entity.id,
            ),
            StagedExtraction(
                extraction_type="relation",
                status="pending",
                source_id=source.id,
                extraction_data={"kind": "inhibits", "confidence": 0.9},
                validation_score=0.78,
            ),
            StagedExtraction(
                extraction_type="claim",
                status="pending",
                source_id=source.id,
                extraction_data={"text": "Aspirin reduces inflammation", "confidence": 0.92},
                validation_score=0.92,
            ),
        ]
        for ex in extractions:
            db.add(ex)

        await db.commit()

        return {
            "message": "Review queue seeded successfully",
            "source_id": str(source.id),
            "entity_id": str(entity.id),
            "extractions_created": len(extractions),
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed review queue: {str(e)}"
        )


@router.post("/seed-ui-categories", response_model=UICategoriesSeedResponse, dependencies=[Depends(check_testing_mode)])
async def seed_ui_categories(db: AsyncSession = Depends(get_db)):
    """
    Seed UI categories for E2E testing.

    Creates sample UI categories so that entity filter tests can exercise
    the category filter section in the filter drawer.

    Only available when TESTING=True.
    """
    from app.models.ui_category import UiCategory

    try:
        categories = [
            UiCategory(slug="drugs", labels={"en": "Drugs", "fr": "Médicaments"}, order=1),
            UiCategory(slug="diseases", labels={"en": "Diseases", "fr": "Maladies"}, order=2),
            UiCategory(slug="mechanisms", labels={"en": "Mechanisms", "fr": "Mécanismes"}, order=3),
        ]
        for cat in categories:
            db.add(cat)

        await db.commit()
        return {"message": "UI categories seeded", "count": len(categories)}

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed UI categories: {str(e)}"
        )


@router.get("/health", response_model=TestHealthResponse, dependencies=[Depends(check_testing_mode)])
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
