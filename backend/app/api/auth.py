"""Authentication endpoints with thin route handlers over focused auth helpers."""

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_handlers import (
    change_current_password,
    deactivate_current_account,
    delete_current_account,
    login_user,
    logout_user,
    read_current_user,
    refresh_user_token,
    register_user,
    request_reset,
    resend_verification,
    reset_user_password,
    update_current_profile,
    verify_user_email_address,
)
from app.config import settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePassword,
    RefreshTokenRequest,
    RequestPasswordReset,
    ResendVerificationEmail,
    ResetPassword,
    Token,
    TokenPair,
    UserRead,
    UserRegister,
    UserSelfUpdate,
    UserUpdate,
    VerifyEmail,
)
from app.services.user_service import UserService
from app.utils.audit import (
    log_account_deletion,
    log_login_attempt,
    log_password_change,
    log_registration,
    log_token_refresh,
)
from app.utils.email import send_password_reset_email, send_verification_email
from app.utils.rate_limit import limiter


router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def register(
    request: Request,
    payload: UserRegister,
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
):
    return await register_user(
        request,
        payload,
        user_service,
        db,
        send_verification_email=send_verification_email,
        log_registration=log_registration,
    )


@router.post("/login", response_model=TokenPair)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
):
    return await login_user(
        request,
        form_data.username,
        form_data.password,
        user_service,
        db,
        log_login_attempt=log_login_attempt,
    )


@router.get("/me", response_model=UserRead)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return read_current_user(current_user)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def refresh_access_token(
    request: Request,
    payload: RefreshTokenRequest,
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
):
    return await refresh_user_token(
        request,
        payload,
        user_service,
        db,
        log_token_refresh=log_token_refresh,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await logout_user(payload, current_user, user_service)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def change_password(
    request: Request,
    payload: ChangePassword,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
):
    return await change_current_password(
        request,
        payload,
        current_user,
        user_service,
        db,
        log_password_change=log_password_change,
    )


@router.put("/me", response_model=UserRead)
async def update_profile(
    payload: UserSelfUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await update_current_profile(payload, current_user, user_service)


@router.post("/deactivate", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def deactivate_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await deactivate_current_account(current_user, user_service)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
):
    return await delete_current_account(
        request,
        current_user,
        user_service,
        db,
        log_account_deletion=log_account_deletion,
    )


@router.post("/verify-email", response_model=UserRead)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def verify_email(
    request: Request,
    payload: VerifyEmail,
    user_service: UserService = Depends(get_user_service),
):
    return await verify_user_email_address(payload, user_service)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def resend_verification_email(
    request: Request,
    payload: ResendVerificationEmail,
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db),
):
    return await resend_verification(
        payload,
        user_service,
        db,
        send_verification_email=send_verification_email,
    )


@router.post("/request-password-reset", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def request_password_reset(
    request: Request,
    payload: RequestPasswordReset,
    user_service: UserService = Depends(get_user_service),
):
    return await request_reset(
        payload,
        user_service,
        send_password_reset_email=send_password_reset_email,
    )


@router.post("/reset-password", response_model=UserRead)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def reset_password(
    request: Request,
    payload: ResetPassword,
    user_service: UserService = Depends(get_user_service),
):
    return await reset_user_password(payload, user_service)
