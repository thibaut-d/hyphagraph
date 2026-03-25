from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from inspect import isawaitable
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.utils.auth import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    hash_token_for_lookup,
    verify_refresh_token,
)
from app.utils.errors import AppException, ErrorCode, UnauthorizedException

logger = logging.getLogger(__name__)


class UserServiceContext(Protocol):
    db: object
    repo: object


async def create_refresh_token_pair(
    service: UserServiceContext,
    user_id: UUID,
    token_version: int,
    *,
    create_access_token_fn=create_access_token,
    generate_refresh_token_fn=generate_refresh_token,
    hash_refresh_token_fn=hash_refresh_token,
    hash_token_for_lookup_fn=hash_token_for_lookup,
) -> tuple[str, str]:
    access_token = create_access_token_fn(data={"sub": str(user_id), "tv": token_version})
    refresh_token = generate_refresh_token_fn()
    token_hash = await hash_refresh_token_fn(refresh_token)
    token_lookup_hash = hash_token_for_lookup_fn(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    try:
        db_refresh_token = RefreshToken(
            user_id=user_id,
            token_lookup_hash=token_lookup_hash,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        add_result = service.db.add(db_refresh_token)
        if isawaitable(add_result):
            await add_result
        await service.db.commit()
        return access_token, refresh_token
    except Exception as e:
        logger.error("Failed to create refresh token for user %s: %s", user_id, e, exc_info=True)
        await service.db.rollback()
        raise


async def refresh_access_token_with_user(
    service: UserServiceContext,
    refresh_token: str,
    *,
    create_access_token_fn=create_access_token,
    generate_refresh_token_fn=generate_refresh_token,
    hash_refresh_token_fn=hash_refresh_token,
    hash_token_for_lookup_fn=hash_token_for_lookup,
    verify_refresh_token_fn=verify_refresh_token,
) -> tuple[str, str, User]:
    lookup_hash = hash_token_for_lookup_fn(refresh_token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_lookup_hash == lookup_hash,
        RefreshToken.is_revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc),
    )
    result = await service.db.execute(stmt)
    matched_token = result.scalar_one_or_none()

    if not matched_token or not await verify_refresh_token_fn(refresh_token, matched_token.token_hash):
        raise UnauthorizedException(
            message="Invalid or expired refresh token",
            details="The provided refresh token is invalid, expired, or has been revoked",
        )

    user = await service.repo.get_by_id(matched_token.user_id)
    if not user or not user.is_active:
        raise UnauthorizedException(
            message="User not found or inactive",
            details="The user associated with this token does not exist or is inactive",
        )

    # Rotate: revoke the consumed token and issue a new one.
    matched_token.is_revoked = True
    matched_token.revoked_at = datetime.now(timezone.utc)

    new_refresh_token = generate_refresh_token_fn()
    new_token_hash = await hash_refresh_token_fn(new_refresh_token)
    new_lookup_hash = hash_token_for_lookup_fn(new_refresh_token)
    expires_at = matched_token.expires_at  # preserve original expiry window

    try:
        new_db_token = RefreshToken(
            user_id=user.id,
            token_lookup_hash=new_lookup_hash,
            token_hash=new_token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        service.db.add(new_db_token)
        await service.db.commit()
    except Exception as e:
        logger.error("Failed to rotate refresh token for user %s: %s", user.id, e, exc_info=True)
        await service.db.rollback()
        raise

    access_token = create_access_token_fn(data={"sub": str(user.id), "tv": user.token_version})
    return access_token, new_refresh_token, user


async def refresh_access_token(
    service: UserServiceContext,
    refresh_token: str,
    **kwargs,
) -> str:
    access_token, _, _user = await refresh_access_token_with_user(service, refresh_token, **kwargs)
    return access_token


async def revoke_refresh_token(
    service: UserServiceContext,
    user_id: UUID,
    refresh_token: str,
    *,
    hash_token_for_lookup_fn=hash_token_for_lookup,
    verify_refresh_token_fn=verify_refresh_token,
) -> None:
    lookup_hash = hash_token_for_lookup_fn(refresh_token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_lookup_hash == lookup_hash,
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False,
    )
    result = await service.db.execute(stmt)
    matched_token = result.scalar_one_or_none()

    if not matched_token or not await verify_refresh_token_fn(refresh_token, matched_token.token_hash):
        raise AppException(
            status_code=404,
            error_code=ErrorCode.NOT_FOUND,
            message="Refresh token not found",
            details="The specified refresh token could not be found or is already revoked",
            context={"user_id": str(user_id)},
        )

    try:
        matched_token.is_revoked = True
        matched_token.revoked_at = datetime.now(timezone.utc)
        await service.db.commit()
    except Exception as e:
        logger.error("Failed to revoke refresh token for user %s: %s", user_id, e, exc_info=True)
        await service.db.rollback()
        raise


async def purge_expired_tokens(db: AsyncSession) -> int:
    """Delete all expired or revoked refresh token rows.

    Rows are safe to delete when they are expired (expires_at < now) or
    explicitly revoked — neither can ever authenticate again.

    Returns:
        Number of rows deleted.
    """
    stmt = delete(RefreshToken).where(
        or_(
            RefreshToken.expires_at < datetime.now(timezone.utc),
            RefreshToken.is_revoked == True,
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    count = result.rowcount
    logger.info("Purged %d expired/revoked refresh token(s)", count)
    return count
