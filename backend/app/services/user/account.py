from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from app.models.user import User
from app.schemas.auth import UserRead, UserRegister, UserUpdate
from app.utils.auth import hash_password, verify_password
from app.utils.errors import UnauthorizedException, ValidationException
from app.services.user.common import load_active_refresh_tokens, to_user_read, user_not_found

logger = logging.getLogger(__name__)


class UserServiceContext(Protocol):
    db: object
    repo: object


async def create_user(
    service: UserServiceContext,
    payload: UserRegister,
    *,
    hash_password_fn=hash_password,
) -> UserRead:
    existing_user = await service.repo.get_by_email(payload.email)
    if existing_user:
        raise ValidationException(
            message="Registration failed",
            field="email",
            details="If this email is not already registered, please try again.",
        )

    hashed_password = await hash_password_fn(payload.password)
    user = User(
        email=payload.email,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
    )

    try:
        await service.repo.create(user)
        await service.db.commit()
        await service.db.refresh(user)
        return to_user_read(user)
    except Exception as e:
        logger.error("Failed to create user '%s': %s", payload.email, e, exc_info=True)
        await service.db.rollback()
        raise


async def get_user(service: UserServiceContext, user_id: UUID) -> UserRead:
    user = await service.repo.get_by_id(user_id)
    if not user:
        raise user_not_found(user_id)
    return to_user_read(user)


async def get_user_by_email(service: UserServiceContext, email: str) -> User | None:
    return await service.repo.get_by_email(email)


async def list_users(service: UserServiceContext) -> list[UserRead]:
    users = await service.repo.list_all()
    return [to_user_read(user) for user in users]


async def update_user(
    service: UserServiceContext,
    user_id: UUID,
    payload: UserUpdate,
    *,
    hash_password_fn=hash_password,
) -> UserRead:
    user = await service.repo.get_by_id(user_id)
    if not user:
        raise user_not_found(user_id)

    try:
        if payload.email is not None:
            existing = await service.repo.get_by_email(payload.email)
            if existing and existing.id != user_id:
                raise ValidationException(
                    message="Email already in use",
                    field="email",
                    details=f"Another user is already using email '{payload.email}'",
                    context={"email": payload.email},
                )
            user.email = payload.email

        if payload.password is not None:
            user.hashed_password = await hash_password_fn(payload.password)

        if payload.is_active is not None:
            user.is_active = payload.is_active

        await service.repo.update(user)
        await service.db.commit()
        await service.db.refresh(user)
        return to_user_read(user)
    except Exception as e:
        logger.error("Failed to update user %s: %s", user_id, e, exc_info=True)
        await service.db.rollback()
        raise


async def deactivate_user(service: UserServiceContext, user_id: UUID) -> None:
    user = await service.repo.get_by_id(user_id)
    if not user:
        raise user_not_found(user_id)

    try:
        user.is_active = False
        await service.repo.update(user)

        active_tokens = await load_active_refresh_tokens(service.db, user_id)
        for token in active_tokens:
            token.is_revoked = True
            token.revoked_at = datetime.now(timezone.utc)

        await service.db.commit()
    except Exception as e:
        logger.error("Failed to deactivate user %s: %s", user_id, e, exc_info=True)
        await service.db.rollback()
        raise


async def delete_user(service: UserServiceContext, user_id: UUID) -> None:
    user = await service.repo.get_by_id(user_id)
    if not user:
        raise user_not_found(user_id)

    try:
        # Revoke active refresh tokens first to prevent in-flight token replay
        active_tokens = await load_active_refresh_tokens(service.db, user_id)
        for token in active_tokens:
            token.is_revoked = True
            token.revoked_at = datetime.now(timezone.utc)

        await service.repo.delete(user)
        await service.db.commit()
    except Exception as e:
        logger.error("Failed to delete user %s: %s", user_id, e, exc_info=True)
        await service.db.rollback()
        raise


async def authenticate_user(
    service: UserServiceContext,
    email: str,
    password: str,
    *,
    verify_password_fn=verify_password,
) -> User:
    user = await service.repo.get_by_email(email)
    if not user or not await verify_password_fn(password, user.hashed_password):
        raise UnauthorizedException(
            message="Incorrect email or password",
            details="Invalid credentials provided",
        )

    if not user.is_active:
        raise UnauthorizedException(
            message="Account is deactivated",
            details="This account has been deactivated. Contact an administrator.",
        )

    return user


async def change_password(
    service: UserServiceContext,
    user_id: UUID,
    current_password: str,
    new_password: str,
    *,
    verify_password_fn=verify_password,
    hash_password_fn=hash_password,
) -> None:
    user = await service.repo.get_by_id(user_id)
    if not user:
        raise user_not_found(user_id)

    if not await verify_password_fn(current_password, user.hashed_password):
        raise UnauthorizedException(
            message="Current password is incorrect",
            details="The provided current password does not match",
        )

    try:
        user.hashed_password = await hash_password_fn(new_password)
        await service.repo.update(user)
        await service.db.commit()
    except Exception as e:
        logger.error("Failed to change password for user %s: %s", user_id, e, exc_info=True)
        await service.db.rollback()
        raise
