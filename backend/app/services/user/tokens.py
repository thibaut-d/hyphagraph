from __future__ import annotations

from datetime import datetime, timedelta, timezone
from inspect import isawaitable
from typing import Protocol
from uuid import UUID

from sqlalchemy import select

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


class UserServiceContext(Protocol):
    db: object
    repo: object


async def create_refresh_token_pair(
    service: UserServiceContext,
    user_id: UUID,
    *,
    create_access_token_fn=create_access_token,
    generate_refresh_token_fn=generate_refresh_token,
    hash_refresh_token_fn=hash_refresh_token,
    hash_token_for_lookup_fn=hash_token_for_lookup,
) -> tuple[str, str]:
    access_token = create_access_token_fn(data={"sub": str(user_id)})
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
    except Exception:
        await service.db.rollback()
        raise


async def refresh_access_token_with_user(
    service: UserServiceContext,
    refresh_token: str,
    *,
    create_access_token_fn=create_access_token,
    hash_token_for_lookup_fn=hash_token_for_lookup,
    verify_refresh_token_fn=verify_refresh_token,
) -> tuple[str, User]:
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

    return create_access_token_fn(data={"sub": str(user.id)}), user


async def refresh_access_token(
    service: UserServiceContext,
    refresh_token: str,
    **kwargs,
) -> str:
    access_token, _ = await refresh_access_token_with_user(service, refresh_token, **kwargs)
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
    except Exception:
        await service.db.rollback()
        raise
