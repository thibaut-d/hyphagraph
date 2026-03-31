from __future__ import annotations

from fastapi import Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.schemas.auth import (
    ChangePassword,
    RequestPasswordReset,
    ResendVerificationEmail,
    ResetPassword,
    Token,
    UserRead,
    UserRegister,
    UserSelfUpdate,
    UserUpdate,
    VerifyEmail,
)
from app.services.user_service import UserService
from app.utils.errors import AppException, ErrorCode, ValidationException

_REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        domain=settings.COOKIE_DOMAIN,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_REFRESH_COOKIE,
        path="/api/auth",
        domain=settings.COOKIE_DOMAIN,
    )


async def register_user(
    request: Request,
    payload: UserRegister,
    user_service: UserService,
    db: AsyncSession,
    *,
    send_verification_email,
    log_registration,
) -> UserRead:
    if settings.EMAIL_VERIFICATION_REQUIRED and not settings.EMAIL_ENABLED:
        raise AppException(
            status_code=500,
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Registration unavailable",
            details="Email verification is required but email sending is disabled. Contact an administrator.",
        )

    try:
        user = await user_service.create(payload)
        if settings.EMAIL_VERIFICATION_REQUIRED:
            token = await user_service.create_verification_token(user.id)
            await send_verification_email(user.email, token)

        await log_registration(
            db=db,
            request=request,
            email=payload.email,
            success=True,
            user_id=user.id,
        )
        return user
    except AppException as error:
        await log_registration(
            db=db,
            request=request,
            email=payload.email,
            success=False,
            error_message=str(error.error_detail.message),
        )
        raise


async def login_user(
    request: Request,
    response: Response,
    email: str,
    password: str,
    user_service: UserService,
    db: AsyncSession,
    *,
    log_login_attempt,
) -> Token:
    try:
        user = await user_service.authenticate(email, password)
        access_token, refresh_token = await user_service.create_refresh_token(user)
        _set_refresh_cookie(response, refresh_token)
        await log_login_attempt(
            db=db,
            request=request,
            email=email,
            success=True,
            user_id=user.id,
        )
        return Token(access_token=access_token, token_type="bearer")
    except AppException as error:
        await log_login_attempt(
            db=db,
            request=request,
            email=email,
            success=False,
            error_message=str(error.error_detail.message),
        )
        raise


def read_current_user(current_user: User) -> UserRead:
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
    )


async def refresh_user_token(
    request: Request,
    response: Response,
    user_service: UserService,
    db: AsyncSession,
    *,
    log_token_refresh,
) -> Token:
    refresh_token = request.cookies.get(_REFRESH_COOKIE)
    if not refresh_token:
        from app.utils.errors import UnauthorizedException
        raise UnauthorizedException(
            message="No refresh token",
            details="Refresh token cookie is missing",
        )
    try:
        access_token, new_refresh_token, user = await user_service.refresh_access_token_with_user(refresh_token)
        _set_refresh_cookie(response, new_refresh_token)
        await log_token_refresh(
            db=db,
            request=request,
            user_id=user.id,
            user_email=user.email,
            success=True,
        )
        return Token(access_token=access_token, token_type="bearer")
    except AppException as error:
        await log_token_refresh(
            db=db,
            request=request,
            user_id=None,
            user_email=None,
            success=False,
            error_message=str(error.error_detail.message),
        )
        raise


async def logout_user(request: Request, response: Response, current_user: User, user_service: UserService) -> None:
    refresh_token = request.cookies.get(_REFRESH_COOKIE)
    if refresh_token:
        try:
            await user_service.revoke_refresh_token(current_user.id, refresh_token)
        except AppException:
            pass  # Already revoked or not found — clear cookie regardless
    _clear_refresh_cookie(response)
    return None


async def change_current_password(
    request: Request,
    payload: ChangePassword,
    current_user: User,
    user_service: UserService,
    db: AsyncSession,
    *,
    log_password_change,
) -> None:
    try:
        await user_service.change_password(
            current_user.id,
            payload.current_password,
            payload.new_password,
        )
        await log_password_change(
            db=db,
            request=request,
            user_id=current_user.id,
            user_email=current_user.email,
            success=True,
        )
        return None
    except AppException as error:
        await log_password_change(
            db=db,
            request=request,
            user_id=current_user.id,
            user_email=current_user.email,
            success=False,
            error_message=str(error.error_detail.message),
        )
        raise


async def update_current_profile(payload: UserSelfUpdate, current_user: User, user_service: UserService) -> UserRead:
    # Construct a UserUpdate with only the email field — password and is_active
    # are admin-only and must not be changeable through the self-service endpoint.
    admin_payload = UserUpdate(email=payload.email)
    return await user_service.update(current_user.id, admin_payload)


async def deactivate_current_account(current_user: User, user_service: UserService) -> None:
    await user_service.deactivate(current_user.id)
    return None


async def delete_current_account(
    request: Request,
    current_user: User,
    user_service: UserService,
    db: AsyncSession,
    *,
    log_account_deletion,
) -> None:
    await log_account_deletion(
        db=db,
        request=request,
        user_id=current_user.id,
        user_email=current_user.email,
    )
    await user_service.delete(current_user.id)
    return None


async def verify_user_email_address(payload: VerifyEmail, user_service: UserService) -> UserRead:
    return await user_service.verify_email(payload.token)


async def resend_verification(
    payload: ResendVerificationEmail,
    user_service: UserService,
    db: AsyncSession,
    *,
    send_verification_email,
) -> None:
    user = await user_service.get_by_email(payload.email)
    # Silent no-op for unknown emails and already-verified accounts — mirrors
    # the password-reset flow and prevents email enumeration via differing responses.
    if not user or user.is_verified:
        return None

    token = await user_service.create_verification_token(user.id)
    if settings.EMAIL_ENABLED:
        await send_verification_email(user.email, token)
    return None


async def request_reset(
    payload: RequestPasswordReset,
    user_service: UserService,
    *,
    send_password_reset_email,
) -> None:
    token = await user_service.request_password_reset(payload.email)
    if token and settings.EMAIL_ENABLED:
        await send_password_reset_email(payload.email, token)
    return None


async def reset_user_password(payload: ResetPassword, user_service: UserService) -> UserRead:
    return await user_service.reset_password(payload.token, payload.new_password)
