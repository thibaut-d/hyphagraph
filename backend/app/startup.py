"""
Application startup tasks.

Handles initialization tasks that should run when the application starts,
such as creating the default admin user and system source.
"""
import logging
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.services.user_service import UserService
from app.schemas.auth import UserRegister

logger = logging.getLogger(__name__)


async def create_admin_user(db: AsyncSession) -> None:
    """
    Create default admin user from environment variables if it doesn't exist.

    Checks if a user with ADMIN_EMAIL already exists. If not, creates
    a new superuser with the credentials from settings.

    This function is idempotent - it's safe to call multiple times.

    Args:
        db: Database session
    """
    user_service = UserService(db)

    try:
        # Check if admin user already exists
        existing_admin = await user_service.get_by_email(settings.ADMIN_EMAIL)

        if existing_admin:
            logger.info(f"Admin user already exists: {settings.ADMIN_EMAIL}")

            # Ensure existing user is a superuser
            if not existing_admin.is_superuser:
                logger.warning(f"User {settings.ADMIN_EMAIL} exists but is not a superuser. Upgrading to superuser.")
                existing_admin.is_superuser = True
                await db.commit()
                logger.info(f"User {settings.ADMIN_EMAIL} upgraded to superuser")

            return

        # Create admin user
        logger.info(f"Creating admin user: {settings.ADMIN_EMAIL}")

        # Use the service to create the user
        admin_data = UserRegister(
            email=settings.ADMIN_EMAIL,
            password=settings.ADMIN_PASSWORD
        )

        admin_user = await user_service.create(admin_data)

        # Upgrade to superuser
        from sqlalchemy import select
        stmt = select(User).where(User.id == admin_user.id)
        result = await db.execute(stmt)
        user = result.scalar_one()
        user.is_superuser = True
        await db.commit()

        logger.info(f"Admin user created successfully: {settings.ADMIN_EMAIL}")
        logger.warning("IMPORTANT: Change the default admin password in production!")

    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        await db.rollback()
        # Don't raise - we don't want to prevent app startup if admin creation fails
        # The admin can be created manually or via migrations


async def create_system_source(db: AsyncSession) -> None:
    """
    Create system source for computed relations if it doesn't exist.

    The system source is used as the provenance for all computed inferences.
    Its ID is stored in settings.SYSTEM_SOURCE_ID.

    This function is idempotent - it's safe to call multiple times.

    Args:
        db: Database session
    """
    try:
        # Check if system source already exists by ID or by title
        if settings.SYSTEM_SOURCE_ID:
            from uuid import UUID
            stmt = select(Source).where(Source.id == UUID(settings.SYSTEM_SOURCE_ID))
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                logger.info(f"System source already exists: {settings.SYSTEM_SOURCE_ID}")
                return

        # Also check by title to avoid duplicates
        stmt = select(Source).join(SourceRevision).where(
            SourceRevision.title == "HyphaGraph Inference Engine",
            SourceRevision.is_current == True
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"System source already exists (found by title): {existing.id}")
            logger.info(f"Consider setting SYSTEM_SOURCE_ID={existing.id} in .env to avoid this check")
            return

        # Create system source
        logger.info("Creating system source for computed inferences...")

        source = Source(id=uuid4())
        db.add(source)
        await db.flush()

        # Create source revision
        revision = SourceRevision(
            source_id=source.id,
            kind="system",
            title="HyphaGraph Inference Engine",
            url="https://github.com/yourusername/hyphagraph",
            year=2025,
            origin="system",
            trust_level=1.0,  # Maximum trust for system computations
            is_current=True,
        )
        db.add(revision)
        await db.commit()

        logger.info(f"System source created: {source.id}")
        logger.info(f"Set SYSTEM_SOURCE_ID={source.id} in your .env.test file to persist across restarts")

        # Note: We can't update settings.SYSTEM_SOURCE_ID here as it's immutable
        # The admin needs to add it to .env.test manually

    except Exception as e:
        logger.error(f"Failed to create system source: {e}")
        await db.rollback()


async def run_startup_tasks(db: AsyncSession) -> None:
    """
    Run all startup tasks.

    Args:
        db: Database session
    """
    logger.info("Running startup tasks...")

    await create_admin_user(db)
    await create_system_source(db)

    logger.info("Startup tasks completed")
