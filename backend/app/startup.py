"""
Application startup tasks.

Handles initialization tasks that should run when the application starts,
such as creating the default admin user.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
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


async def run_startup_tasks(db: AsyncSession) -> None:
    """
    Run all startup tasks.

    Args:
        db: Database session
    """
    logger.info("Running startup tasks...")

    await create_admin_user(db)

    logger.info("Startup tasks completed")
