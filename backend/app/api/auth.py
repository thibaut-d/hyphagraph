"""
Authentication endpoints for user registration, login, and profile.

Implements custom JWT-based authentication (NOT FastAPI Users).
Uses UserService for business logic (matches architectural pattern).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    UserRegister,
    UserRead,
    UserUpdate,
    Token,
    TokenPair,
    RefreshTokenRequest,
    ChangePassword,
    VerifyEmail,
    ResendVerificationEmail,
    RequestPasswordReset,
    ResetPassword,
)
from app.services.user_service import UserService
from app.dependencies.auth import get_current_user
from app.utils.rate_limit import limiter
from app.utils.audit import (
    log_registration,
    log_login_attempt,
    log_password_change,
    log_account_deletion,
    log_token_refresh,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Dependency to get UserService instance."""
    return UserService(db)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def register(
    request: Request,
    payload: UserRegister,
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user.

    Creates a new user account with hashed password.
    Email must be unique.

    Rate limited to prevent registration spam and enumeration attacks.

    Args:
        request: FastAPI request (required for rate limiting and audit logging)
        payload: User registration data (email, password)
        user_service: User service instance
        db: Database session (for audit logging)

    Returns:
        Created user information (without password)

    Raises:
        HTTPException 400: If email already registered
        HTTPException 429: If rate limit exceeded
    """
    from app.utils.email import send_verification_email

    try:
        user = await user_service.create(payload)

        # Create verification token if email verification is enabled
        if settings.EMAIL_VERIFICATION_REQUIRED:
            token = await user_service.create_verification_token(user.id)

            # Send verification email
            if settings.EMAIL_ENABLED:
                await send_verification_email(user.email, token)

        # Log successful registration
        await log_registration(
            db=db,
            request=request,
            email=payload.email,
            success=True,
            user_id=user.id
        )

        return user

    except HTTPException as e:
        # Log failed registration
        await log_registration(
            db=db,
            request=request,
            email=payload.email,
            success=False,
            error_message=e.detail
        )
        raise


@router.post("/login", response_model=TokenPair)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Login to get JWT access token and refresh token.

    Uses OAuth2 password flow (standard FastAPI pattern).
    Note: OAuth2PasswordRequestForm uses 'username' field, but we treat it as email.

    Rate limited to prevent brute force attacks.

    Args:
        request: FastAPI request (required for rate limiting and audit logging)
        form_data: OAuth2 form data (username=email, password)
        user_service: User service instance
        db: Database session (for audit logging)

    Returns:
        JWT access token and refresh token pair

    Raises:
        HTTPException 401: If credentials are invalid
        HTTPException 429: If rate limit exceeded
    """
    try:
        # Authenticate user
        user = await user_service.authenticate(form_data.username, form_data.password)

        # Create token pair
        access_token, refresh_token = await user_service.create_refresh_token(user.id)

        # Log successful login
        await log_login_attempt(
            db=db,
            request=request,
            email=form_data.username,
            success=True,
            user_id=user.id
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    except HTTPException as e:
        # Log failed login
        await log_login_attempt(
            db=db,
            request=request,
            email=form_data.username,
            success=False,
            error_message=e.detail
        )
        raise


@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.

    Args:
        current_user: Current authenticated user (from dependency)

    Returns:
        Current user information
    """
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
    )


@router.post("/refresh", response_model=Token)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def refresh_access_token(
    request: Request,
    payload: RefreshTokenRequest,
    user_service: UserService = Depends(get_user_service)
):
    """
    Refresh access token using a valid refresh token.

    Validates the refresh token and issues a new access token.
    Does NOT rotate the refresh token (single refresh token per login session).

    Rate limited to prevent token refresh abuse.

    Args:
        request: FastAPI request (required for rate limiting)
        payload: Refresh token request containing the refresh token
        user_service: User service instance

    Returns:
        New JWT access token

    Raises:
        HTTPException 401: If refresh token is invalid, expired, or revoked
        HTTPException 429: If rate limit exceeded
    """
    access_token = await user_service.refresh_access_token(payload.refresh_token)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Logout by revoking the refresh token.

    Marks the refresh token as revoked, preventing future token refreshes.
    Access tokens remain valid until expiry (stateless JWT limitation).

    Args:
        payload: Refresh token to revoke
        current_user: Current authenticated user (from access token)
        user_service: User service instance

    Returns:
        No content (204)

    Raises:
        HTTPException 404: If refresh token not found
    """
    await user_service.revoke_refresh_token(current_user.id, payload.refresh_token)
    return None


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def change_password(
    request: Request,
    payload: ChangePassword,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Change the current user's password.

    Requires authentication and current password verification.

    Rate limited to prevent brute force attacks on password verification.

    Args:
        request: FastAPI request (required for rate limiting and audit logging)
        payload: Current and new password
        current_user: Current authenticated user
        user_service: User service instance
        db: Database session (for audit logging)

    Returns:
        No content (204)

    Raises:
        HTTPException 401: If current password is incorrect
        HTTPException 429: If rate limit exceeded
    """
    try:
        await user_service.change_password(
            current_user.id,
            payload.current_password,
            payload.new_password
        )

        # Log successful password change
        await log_password_change(
            db=db,
            request=request,
            user_id=current_user.id,
            user_email=current_user.email,
            success=True
        )

        return None

    except HTTPException as e:
        # Log failed password change
        await log_password_change(
            db=db,
            request=request,
            user_id=current_user.id,
            user_email=current_user.email,
            success=False,
            error_message=e.detail
        )
        raise


@router.put("/me", response_model=UserRead)
async def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update the current user's profile.

    Allows updating email and other profile fields.
    To change password, use the /change-password endpoint instead.

    Args:
        payload: Fields to update
        current_user: Current authenticated user
        user_service: User service instance

    Returns:
        Updated user information

    Raises:
        HTTPException 400: If email already in use
    """
    return await user_service.update(current_user.id, payload)


@router.post("/deactivate", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def deactivate_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """
    Deactivate the current user's account (soft delete).

    This action is reversible and will:
    - Set the user account as inactive (is_active = False)
    - Revoke all active refresh tokens
    - Preserve all user data

    User can reactivate by logging in again, which will set is_active back to True.

    Rate limited to prevent accidental rapid deactivations.

    Args:
        request: FastAPI request (required for rate limiting)
        current_user: Current authenticated user
        user_service: User service instance

    Returns:
        No content (204)

    Raises:
        HTTPException 429: If rate limit exceeded
    """
    await user_service.deactivate(current_user.id)
    return None


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete the current user's account.

    This action is permanent and will:
    - Delete the user account
    - Revoke all refresh tokens (cascading delete)
    - Remove all user data

    Rate limited to prevent accidental rapid deletions.

    Args:
        request: FastAPI request (required for rate limiting and audit logging)
        current_user: Current authenticated user
        user_service: User service instance
        db: Database session (for audit logging)

    Returns:
        No content (204)

    Raises:
        HTTPException 429: If rate limit exceeded
    """
    # Log account deletion before deleting (user will be gone after)
    await log_account_deletion(
        db=db,
        request=request,
        user_id=current_user.id,
        user_email=current_user.email
    )

    await user_service.delete(current_user.id)
    return None


@router.post("/verify-email", response_model=UserRead)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def verify_email(
    request: Request,
    payload: VerifyEmail,
    user_service: UserService = Depends(get_user_service)
):
    """
    Verify user email address with verification token.

    Marks the user's email as verified and clears the verification token.

    Args:
        request: FastAPI request (required for rate limiting)
        payload: Verification token
        user_service: User service instance

    Returns:
        Verified user information

    Raises:
        HTTPException 400: If token is invalid or expired
        HTTPException 429: If rate limit exceeded
    """
    return await user_service.verify_email(payload.token)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def resend_verification_email(
    request: Request,
    payload: ResendVerificationEmail,
    user_service: UserService = Depends(get_user_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Resend email verification link.

    Generates a new verification token and sends a verification email.
    Can be used if the original verification email was lost or expired.

    Args:
        request: FastAPI request (required for rate limiting)
        payload: Email address to resend verification to
        user_service: User service instance
        db: Database session

    Returns:
        No content (204)

    Raises:
        HTTPException 404: If user not found
        HTTPException 400: If user already verified
        HTTPException 429: If rate limit exceeded
    """
    from app.utils.email import send_verification_email

    # Get user by email
    user = await user_service.get_by_email(payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if already verified
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    # Create new verification token
    token = await user_service.create_verification_token(user.id)

    # Send verification email
    if settings.EMAIL_ENABLED:
        await send_verification_email(user.email, token)

    return None


@router.post("/request-password-reset", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def request_password_reset(
    request: Request,
    payload: RequestPasswordReset,
    user_service: UserService = Depends(get_user_service)
):
    """
    Request password reset email.

    Generates a reset token and sends an email with reset link.
    Always returns success even if email doesn't exist (security best practice
    to prevent email enumeration).

    Rate limited to prevent abuse.

    Args:
        request: FastAPI request (required for rate limiting)
        payload: Email address to send password reset link
        user_service: User service instance

    Returns:
        No content (204) - always succeeds regardless of whether email exists

    Raises:
        HTTPException 429: If rate limit exceeded
    """
    from app.utils.email import send_password_reset_email

    # Request reset token (returns None if user doesn't exist)
    token = await user_service.request_password_reset(payload.email)

    # Send email if user exists and email is enabled
    if token and settings.EMAIL_ENABLED:
        await send_password_reset_email(payload.email, token)

    # Always return success (don't reveal if user exists)
    return None


@router.post("/reset-password", response_model=UserRead)
@limiter.limit(f"{settings.AUTH_RATE_LIMIT_PER_MINUTE}/minute")
async def reset_password(
    request: Request,
    payload: ResetPassword,
    user_service: UserService = Depends(get_user_service)
):
    """
    Reset password with reset token.

    Uses the token from the password reset email to set a new password.

    Rate limited to prevent brute force attacks on reset tokens.

    Args:
        request: FastAPI request (required for rate limiting)
        payload: Reset token and new password
        user_service: User service instance

    Returns:
        Updated user information

    Raises:
        HTTPException 400: If token is invalid or expired
        HTTPException 429: If rate limit exceeded
    """
    return await user_service.reset_password(payload.token, payload.new_password)