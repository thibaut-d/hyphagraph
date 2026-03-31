"""
Admin service — user management operations for superusers.

Encapsulates all domain logic for admin user management, including
self-modification guards and last-superuser protection.
"""
import logging

from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ui_category import UiCategory
from app.models.user import User
from app.schemas.admin import UserListItemRead, UserStatsRead, UserUpdate
from app.schemas.ui_category import UICategoryRead, UICategoryWrite
from app.utils.errors import AppException, ErrorCode, ValidationException

logger = logging.getLogger(__name__)


def _cat_to_read(cat: UiCategory) -> UICategoryRead:
    return UICategoryRead(
        id=cat.id,
        slug=cat.slug,
        labels=cat.labels,
        description=cat.description,
        order=cat.order,
        created_at=getattr(cat, "created_at", None),
        updated_at=getattr(cat, "updated_at", None),
    )


def _to_read(user: User) -> UserListItemRead:
    return UserListItemRead(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


def _category_to_read(category: UiCategory) -> UICategoryRead:
    return UICategoryRead(
        id=category.id,
        slug=category.slug,
        labels=category.labels,
        description=category.description,
        order=category.order,
        created_at=getattr(category, "created_at", None),
        updated_at=getattr(category, "updated_at", None),
    )


class AdminService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_stats(self) -> UserStatsRead:
        """Return aggregate user counts for the admin dashboard."""
        total = await self.db.scalar(select(func.count()).select_from(User))
        active = await self.db.scalar(
            select(func.count()).select_from(User).where(User.is_active == True)
        )
        supers = await self.db.scalar(
            select(func.count()).select_from(User).where(User.is_superuser == True)
        )
        verified = await self.db.scalar(
            select(func.count()).select_from(User).where(User.is_verified == True)
        )
        return UserStatsRead(
            total_users=total or 0,
            active_users=active or 0,
            superusers=supers or 0,
            verified_users=verified or 0,
        )

    async def list_users(self, limit: int = 50, offset: int = 0) -> list[UserListItemRead]:
        """Return a paginated list of all users."""
        stmt = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return [_to_read(u) for u in result.scalars().all()]

    async def get_user(self, user_id: UUID) -> UserListItemRead:
        """Return user details by ID. Raises 404 if not found."""
        user = await self._require_user(user_id)
        return _to_read(user)

    async def update_user(
        self, user_id: UUID, updates: UserUpdate, admin_id: UUID
    ) -> UserListItemRead:
        """
        Apply admin flag updates to a user.

        Guards:
        - Admin cannot deactivate themselves.
        - Admin cannot remove their own superuser status.
        - Cannot demote the last remaining superuser.
        """
        user = await self._require_user(user_id)

        # Self-modification guards
        if user.id == admin_id:
            if updates.is_active is False:
                raise ValidationException(
                    message="Cannot deactivate yourself",
                    details="You cannot deactivate your own account",
                )
            if updates.is_superuser is False:
                raise ValidationException(
                    message="Cannot demote yourself from superuser",
                    details="You cannot remove your own superuser privileges",
                )

        # Last-superuser protection
        if updates.is_superuser is False and user.is_superuser:
            super_count = await self.db.scalar(
                select(func.count()).select_from(User).where(User.is_superuser == True)
            )
            if (super_count or 0) <= 1:
                raise ValidationException(
                    message="Cannot demote last superuser",
                    details="At least one superuser must remain in the system",
                )

        role_changed = False
        if updates.is_active is not None:
            if user.is_active != updates.is_active:
                role_changed = True
            user.is_active = updates.is_active
        if updates.is_superuser is not None:
            if user.is_superuser != updates.is_superuser:
                role_changed = True
            user.is_superuser = updates.is_superuser
        if updates.is_verified is not None:
            user.is_verified = updates.is_verified

        # Invalidate outstanding access tokens when privileges change
        if role_changed:
            user.token_version += 1

        try:
            await self.db.commit()
            await self.db.refresh(user)
        except Exception as e:
            logger.error("Failed to update user %s: %s", user_id, e, exc_info=True)
            await self.db.rollback()
            raise
        return _to_read(user)

    async def delete_user(self, user_id: UUID, admin_id: UUID) -> None:
        """
        Delete a user.

        Guard: Admin cannot delete themselves.
        """
        if user_id == admin_id:
            raise ValidationException(
                message="Cannot delete yourself",
                details="You cannot delete your own account",
            )
        user = await self._require_user(user_id)
        try:
            await self.db.delete(user)
            await self.db.commit()
        except Exception as e:
            logger.error("Failed to delete user %s: %s", user_id, e, exc_info=True)
            await self.db.rollback()
            raise

    async def list_categories(self) -> list[UICategoryRead]:
        """Return all UI categories ordered for admin management."""
        result = await self.db.execute(select(UiCategory).order_by(UiCategory.order))
        return [_category_to_read(category) for category in result.scalars().all()]

    async def get_category(self, category_id: UUID) -> UiCategory:
        """Return a UI category model or raise 404 if missing."""
        result = await self.db.execute(select(UiCategory).where(UiCategory.id == category_id))
        category = result.scalar_one_or_none()
        if not category:
            raise AppException(
                status_code=404,
                error_code=ErrorCode.NOT_FOUND,
                message="Category not found",
                details=f"No UI category with ID '{category_id}'.",
            )
        return category

    async def create_category(self, payload: UICategoryWrite) -> UICategoryRead:
        """Create a new UI category."""
        category = UiCategory(
            slug=payload.slug,
            labels=payload.labels,
            description=payload.description,
            order=payload.order,
        )
        self.db.add(category)
        try:
            await self.db.commit()
            await self.db.refresh(category)
        except IntegrityError:
            await self.db.rollback()
            raise AppException(
                status_code=409,
                error_code=ErrorCode.ENTITY_SLUG_CONFLICT,
                message="Category slug already exists",
                field="slug",
                details=f"A UI category with slug '{payload.slug}' already exists.",
            )
        return _category_to_read(category)

    async def update_category(self, category_id: UUID, payload: UICategoryWrite) -> UICategoryRead:
        """Update an existing UI category."""
        category = await self.get_category(category_id)
        category.slug = payload.slug
        category.labels = payload.labels
        category.description = payload.description
        category.order = payload.order
        try:
            await self.db.commit()
            await self.db.refresh(category)
        except IntegrityError:
            await self.db.rollback()
            raise AppException(
                status_code=409,
                error_code=ErrorCode.ENTITY_SLUG_CONFLICT,
                message="Category slug already exists",
                field="slug",
                details=f"A UI category with slug '{payload.slug}' already exists.",
            )
        return _category_to_read(category)

    async def delete_category(self, category_id: UUID) -> None:
        """Delete a UI category or raise 404 if it does not exist."""
        category = await self.get_category(category_id)
        await self.db.delete(category)
        await self.db.commit()

    # -------------------------------------------------------------------------
    # UI Category management
    # -------------------------------------------------------------------------

    async def list_categories(self) -> list[UICategoryRead]:
        """Return all UI categories ordered by display order."""
        result = await self.db.execute(select(UiCategory).order_by(UiCategory.order))
        return [_cat_to_read(c) for c in result.scalars().all()]

    async def create_category(self, payload: UICategoryWrite) -> UICategoryRead:
        """Create a new UI category. Raises 409 on slug conflict."""
        cat = UiCategory(
            slug=payload.slug,
            labels=payload.labels,
            description=payload.description,
            order=payload.order,
        )
        self.db.add(cat)
        try:
            await self.db.commit()
            await self.db.refresh(cat)
        except IntegrityError:
            await self.db.rollback()
            raise AppException(
                status_code=409,
                error_code=ErrorCode.ENTITY_SLUG_CONFLICT,
                message="Category slug already exists",
                field="slug",
                details=f"A UI category with slug '{payload.slug}' already exists.",
            )
        return _cat_to_read(cat)

    async def get_category(self, category_id: UUID) -> UICategoryRead:
        """Return a UI category by ID. Raises 404 if not found."""
        cat = await self._require_category(category_id)
        return _cat_to_read(cat)

    async def update_category(self, category_id: UUID, payload: UICategoryWrite) -> UICategoryRead:
        """Update a UI category. Raises 404 if not found, 409 on slug conflict."""
        cat = await self._require_category(category_id)
        cat.slug = payload.slug
        cat.labels = payload.labels
        cat.description = payload.description
        cat.order = payload.order
        try:
            await self.db.commit()
            await self.db.refresh(cat)
        except IntegrityError:
            await self.db.rollback()
            raise AppException(
                status_code=409,
                error_code=ErrorCode.ENTITY_SLUG_CONFLICT,
                message="Category slug already exists",
                field="slug",
                details=f"A UI category with slug '{payload.slug}' already exists.",
            )
        return _cat_to_read(cat)

    async def delete_category(self, category_id: UUID) -> None:
        """Delete a UI category. Raises 404 if not found."""
        cat = await self._require_category(category_id)
        await self.db.delete(cat)
        await self.db.commit()

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    async def _require_user(self, user_id: UUID) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise AppException(
                status_code=404,
                error_code=ErrorCode.USER_NOT_FOUND,
                message="User not found",
                details=f"User with ID '{user_id}' does not exist",
                context={"user_id": str(user_id)},
            )
        return user

    async def _require_category(self, category_id: UUID) -> UiCategory:
        result = await self.db.execute(select(UiCategory).where(UiCategory.id == category_id))
        cat = result.scalar_one_or_none()
        if not cat:
            raise AppException(
                status_code=404,
                error_code=ErrorCode.NOT_FOUND,
                message="Category not found",
                details=f"No UI category with ID '{category_id}'.",
            )
        return cat
