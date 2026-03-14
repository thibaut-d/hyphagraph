from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import UserRead
from app.utils.errors import AppException, ErrorCode


def to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


def user_not_found(user_id: UUID) -> AppException:
    return AppException(
        status_code=404,
        error_code=ErrorCode.USER_NOT_FOUND,
        message="User not found",
        details=f"User with ID '{user_id}' does not exist",
        context={"user_id": str(user_id)},
    )


async def load_active_refresh_tokens(db: AsyncSession, user_id: UUID) -> list[RefreshToken]:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
        )
    )
    return list(result.scalars().all())
