"""
Application startup and bootstrap tasks.

Startup tasks run automatically when the app launches and must stay non-privileged.
Bootstrap tasks are explicit setup operations used for test resets or initial environment setup.
"""
import logging
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.models.source import Source
from app.models.source_revision import SourceRevision
from app.services.user_service import UserService
from app.schemas.auth import UserRegister

logger = logging.getLogger(__name__)


async def bootstrap_admin_user(db: AsyncSession) -> None:
    """
    Create default admin user from configured bootstrap credentials if it doesn't exist.

    This is an explicit bootstrap operation and must not run automatically at app startup.

    This function is idempotent - it's safe to call multiple times.

    Args:
        db: Database session
    """
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        raise RuntimeError(
            "ADMIN_EMAIL and ADMIN_PASSWORD must be configured for admin bootstrap"
        )

    user_service = UserService(db)

    try:
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
        logger.info(f"Bootstrapping admin user: {settings.ADMIN_EMAIL}")

        # Use the service to create the user
        admin_data = UserRegister(
            email=settings.ADMIN_EMAIL,
            password=settings.ADMIN_PASSWORD,
            password_confirmation=settings.ADMIN_PASSWORD,
        )

        admin_user = await user_service.create(admin_data)

        # Upgrade to superuser
        stmt = select(User).where(User.id == admin_user.id)
        result = await db.execute(stmt)
        user = result.scalar_one()
        user.is_superuser = True
        await db.commit()

        logger.info(f"Admin user bootstrapped successfully: {settings.ADMIN_EMAIL}")
        logger.warning("Bootstrap admin credentials should be rotated outside test environments.")

    except IntegrityError:
        # Concurrent bootstrap: another process created the admin user between
        # our existence check and our insert. Roll back and treat as success.
        await db.rollback()
        logger.info(f"Admin user already created by concurrent process: {settings.ADMIN_EMAIL}")
    except Exception as e:
        logger.error(f"Failed to bootstrap admin user: {e}")
        await db.rollback()
        raise


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
        raise


async def run_startup_tasks(db: AsyncSession) -> None:
    """
    Run non-privileged automatic startup tasks.

    Args:
        db: Database session
    """
    logger.info("Running startup tasks...")
    await create_system_source(db)
    logger.info("Startup tasks completed")


async def run_bootstrap_tasks(db: AsyncSession) -> None:
    """
    Run explicit bootstrap/setup tasks.

    This path is intended for test reset helpers or manual environment bootstrap,
    not for normal application startup.

    Args:
        db: Database session
    """
    logger.info("Running bootstrap tasks...")
    await create_system_source(db)
    await bootstrap_admin_user(db)
    logger.info("Bootstrap tasks completed")
