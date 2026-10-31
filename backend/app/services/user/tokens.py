from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from inspect import isawaitable
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import and_, delete, or_, select
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


def _as_utc(value: datetime) -> datetime:
    # SQLite (tests) returns naive datetimes; Postgres returns aware ones.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def _rotated_within_grace(service: UserServiceContext, token: RefreshToken) -> bool:
    """Whether a revoked token may still be used because it was *just* rotated.

    Accepted only if it was revoked by rotation (has a successor) less than
    REFRESH_TOKEN_REUSE_GRACE_SECONDS ago, and the end of its rotation chain is
    still active. Logout and password changes revoke the active successor, so
    they keep cutting access immediately.
    """
    now = datetime.now(timezone.utc)
    grace = timedelta(seconds=settings.REFRESH_TOKEN_REUSE_GRACE_SECONDS)
    if token.replaced_by_id is None or token.revoked_at is None:
        return False
    if now - _as_utc(token.revoked_at) > grace:
        return False

    current = token
    for _ in range(10):  # chain is short within the grace window; bound it anyway
        successor = await service.db.get(RefreshToken, current.replaced_by_id)
        if successor is None or _as_utc(successor.expires_at) <= now:
            return False
        if not successor.is_revoked:
            return True
        if successor.replaced_by_id is None or successor.revoked_at is None:
            return False  # revoked by logout / password change, not by rotation
        if now - _as_utc(successor.revoked_at) > grace:
            return False
        current = successor
    return False


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
    invalid = UnauthorizedException(
        message="Invalid or expired refresh token",
        details="The provided refresh token is invalid, expired, or has been revoked",
    )
    lookup_hash = hash_token_for_lookup_fn(refresh_token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_lookup_hash == lookup_hash,
        RefreshToken.expires_at > datetime.now(timezone.utc),
    )
    result = await service.db.execute(stmt)
    matched_token = result.scalar_one_or_none()

    if not matched_token or not await verify_refresh_token_fn(refresh_token, matched_token.token_hash):
        raise invalid

    reused_within_grace = False
    if matched_token.is_revoked:
        if not await _rotated_within_grace(service, matched_token):
            raise invalid
        reused_within_grace = True

    user = await service.repo.get_by_id(matched_token.user_id)
    if not user or not user.is_active:
        raise UnauthorizedException(
            message="User not found or inactive",
            details="The user associated with this token does not exist or is inactive",
        )

    new_refresh_token = generate_refresh_token_fn()
    new_token_hash = await hash_refresh_token_fn(new_refresh_token)
    new_lookup_hash = hash_token_for_lookup_fn(new_refresh_token)
    expires_at = matched_token.expires_at  # preserve original expiry window

    try:
        new_db_token = RefreshToken(
            id=uuid4(),
            user_id=user.id,
            token_lookup_hash=new_lookup_hash,
            token_hash=new_token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        service.db.add(new_db_token)
        # Insert the successor before the UPDATE that references it (no ORM
        # relationship, so the unit of work cannot infer the FK ordering).
        await service.db.flush()
        if not reused_within_grace:
            # Rotate: revoke the consumed token and link it to its successor.
            # On a grace reuse the existing successor stays valid (another tab
            # or the cookie jar may hold it); we only issue an extra token.
            matched_token.is_revoked = True
            matched_token.revoked_at = datetime.now(timezone.utc)
            matched_token.replaced_by_id = new_db_token.id
        await service.db.commit()
    except Exception as e:
        logger.error("Failed to rotate refresh token for user %s: %s", user.id, e, exc_info=True)
        await service.db.rollback()
        raise

    if reused_within_grace:
        logger.info("Accepted recently rotated refresh token for user %s (grace period)", user.id)
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
    revoked — except tokens revoked within the rotation grace window, which can
    still be exchanged once (see _rotated_within_grace).

    Returns:
        Number of rows deleted.
    """
    stmt = delete(RefreshToken).where(
        or_(
            RefreshToken.expires_at < datetime.now(timezone.utc),
            and_(
                RefreshToken.is_revoked == True,
                or_(
                    RefreshToken.revoked_at.is_(None),
                    RefreshToken.revoked_at
                    < datetime.now(timezone.utc)
                    - timedelta(seconds=settings.REFRESH_TOKEN_REUSE_GRACE_SECONDS),
                ),
            ),
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    count = result.rowcount
    logger.info("Purged %d expired/revoked refresh token(s)", count)
    return count
