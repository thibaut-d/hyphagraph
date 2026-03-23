from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.schemas.auth import UserRead
from app.utils.auth import hash_password, hash_token_for_lookup
from app.utils.email import generate_verification_token
from app.utils.errors import ValidationException
from app.services.user.common import load_active_refresh_tokens, to_user_read, user_not_found

logger = logging.getLogger(__name__)


class UserServiceContext(Protocol):
    db: object
    repo: object


async def create_verification_token(
    service: UserServiceContext,
    user_id: UUID,
    *,
    generate_verification_token_fn=generate_verification_token,
) -> str:
    user = await service.repo.get_by_id(user_id)
    if not user:
        raise user_not_found(user_id)

    try:
        token = generate_verification_token_fn()
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
        )
        user.verification_token = hash_token_for_lookup(token)
        user.verification_token_expires_at = expires_at
        await service.repo.update(user)
        await service.db.commit()
        return token
    except Exception as e:
        logger.error("Failed to create verification token for user %s: %s", user_id, e, exc_info=True)
        await service.db.rollback()
        raise


async def verify_email(service: UserServiceContext, token: str) -> UserRead:
    result = await service.db.execute(select(User).where(User.verification_token == hash_token_for_lookup(token)))
    user = result.scalar_one_or_none()
    if not user:
        raise ValidationException(
            message="Invalid verification token",
            details="The provided verification token does not exist",
        )

    if (
        user.verification_token_expires_at is None
        or user.verification_token_expires_at < datetime.now(timezone.utc)
    ):
        raise ValidationException(
            message="Verification token has expired",
            details="Please request a new verification email",
        )

    try:
        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires_at = None
        await service.repo.update(user)
        await service.db.commit()
        await service.db.refresh(user)
        return to_user_read(user)
    except Exception as e:
        logger.error("Failed to verify email (token redacted): %s", e, exc_info=True)
        await service.db.rollback()
        raise


async def request_password_reset(
    service: UserServiceContext,
    email: str,
    *,
    generate_verification_token_fn=generate_verification_token,
) -> str | None:
    user = await service.repo.get_by_email(email)
    if not user:
        return None

    try:
        token = generate_verification_token_fn()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        user.reset_token = hash_token_for_lookup(token)
        user.reset_token_expires_at = expires_at
        await service.repo.update(user)
        await service.db.commit()
        return token
    except Exception as e:
        logger.error("Failed to store password reset token: %s", e, exc_info=True)
        await service.db.rollback()
        raise


async def reset_password(
    service: UserServiceContext,
    token: str,
    new_password: str,
    *,
    hash_password_fn=hash_password,
) -> UserRead:
    result = await service.db.execute(select(User).where(User.reset_token == hash_token_for_lookup(token)))
    user = result.scalar_one_or_none()
    if not user:
        raise ValidationException(
            message="Invalid or expired reset token",
            details="The provided reset token does not exist or has already been used",
        )

    if user.reset_token_expires_at is None or user.reset_token_expires_at < datetime.now(timezone.utc):
        raise ValidationException(
            message="Reset token has expired",
            details="Please request a new password reset",
        )

    try:
        user.hashed_password = await hash_password_fn(new_password)
        user.reset_token = None
        user.reset_token_expires_at = None
        await service.repo.update(user)

        # Revoke all active refresh tokens so existing sessions are invalidated
        # after a password reset (prevents session fixation attacks).
        active_tokens = await load_active_refresh_tokens(service.db, user.id)
        for token in active_tokens:
            token.is_revoked = True
            token.revoked_at = datetime.now(timezone.utc)

        await service.db.commit()
        await service.db.refresh(user)
        return to_user_read(user)
    except Exception as e:
        logger.error("Failed to reset password (token redacted): %s", e, exc_info=True)
        await service.db.rollback()
        raise
