from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime, timedelta, timezone

from app.schemas.auth import UserRegister, UserRead, UserUpdate
from app.repositories.user_repo import UserRepository
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_refresh_token,
    hash_token_for_lookup
)
from app.utils.email import (
    generate_verification_token,
    send_verification_email,
    send_password_reset_email,
)
from app.config import settings
from app.utils.errors import (
    AppException,
    ErrorCode,
    ValidationException,
    UnauthorizedException,
)


class UserService:
    """
    Business logic layer for User management.

    Handles:
    - User CRUD operations
    - Password management
    - Refresh token management
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UserRepository(db)

    async def create(self, payload: UserRegister) -> UserRead:
        """
        Register a new user.

        Args:
            payload: User registration data (email, password)

        Returns:
            Created user information (without password)

        Raises:
            ValidationException: If email already registered
        """
        # Check if email already exists
        existing_user = await self.repo.get_by_email(payload.email)
        if existing_user:
            raise ValidationException(
                message="Email already registered",
                field="email",
                details=f"An account with email '{payload.email}' already exists",
                context={"email": payload.email}
            )

        # Hash password
        hashed_password = await hash_password(payload.password)

        # Create user
        user = User(
            email=payload.email,
            hashed_password=hashed_password,
            is_active=True,
            is_superuser=False,
        )

        try:
            await self.repo.create(user)
            await self.db.commit()
            await self.db.refresh(user)

            return UserRead(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                is_verified=user.is_verified,
                created_at=user.created_at,
            )

        except Exception:
            await self.db.rollback()
            raise

    async def get(self, user_id: UUID) -> UserRead:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User information

        Raises:
            AppException: If user not found
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise AppException(
                status_code=404,
                error_code=ErrorCode.USER_NOT_FOUND,
                message="User not found",
                details=f"User with ID '{user_id}' does not exist",
                context={"user_id": str(user_id)}
            )

        return UserRead(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_verified=user.is_verified,
            created_at=user.created_at,
        )

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email (returns model, not schema).

        Used internally for authentication.

        Args:
            email: User email address

        Returns:
            User model or None
        """
        return await self.repo.get_by_email(email)

    async def list_all(self) -> list[UserRead]:
        """
        List all users.

        Returns:
            List of all users
        """
        users = await self.repo.list_all()
        return [
            UserRead(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                created_at=user.created_at,
            )
            for user in users
        ]

    async def update(self, user_id: UUID, payload: UserUpdate) -> UserRead:
        """
        Update user information.

        Args:
            user_id: User UUID
            payload: Fields to update

        Returns:
            Updated user information

        Raises:
            AppException: If user not found
            ValidationException: If email already in use
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise AppException(
                status_code=404,
                error_code=ErrorCode.USER_NOT_FOUND,
                message="User not found",
                details=f"User with ID '{user_id}' does not exist",
                context={"user_id": str(user_id)}
            )

        try:
            # Update email if provided
            if payload.email is not None:
                # Check if email is already in use by another user
                existing = await self.repo.get_by_email(payload.email)
                if existing and existing.id != user_id:
                    raise ValidationException(
                        message="Email already in use",
                        field="email",
                        details=f"Another user is already using email '{payload.email}'",
                        context={"email": payload.email}
                    )
                user.email = payload.email

            # Update password if provided
            if payload.password is not None:
                user.hashed_password = await hash_password(payload.password)

            # Update is_active if provided
            if payload.is_active is not None:
                user.is_active = payload.is_active

            await self.repo.update(user)
            await self.db.commit()
            await self.db.refresh(user)

            return UserRead(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                is_verified=user.is_verified,
                created_at=user.created_at,
            )

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def deactivate(self, user_id: UUID) -> None:
        """
        Deactivate a user account (soft delete).

        Sets is_active to False and revokes all refresh tokens.
        User can reactivate by logging in again.

        Args:
            user_id: User UUID

        Raises:
            AppException: If user not found
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise AppException(
                status_code=404,
                error_code=ErrorCode.USER_NOT_FOUND,
                message="User not found",
                details=f"User with ID '{user_id}' does not exist",
                context={"user_id": str(user_id)}
            )

        try:
            # Set user as inactive
            user.is_active = False
            await self.repo.update(user)

            # Revoke all active refresh tokens for this user
            stmt = select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False
            )
            result = await self.db.execute(stmt)
            active_tokens = result.scalars().all()

            for token in active_tokens:
                token.is_revoked = True
                token.revoked_at = datetime.now(timezone.utc)

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

    async def delete(self, user_id: UUID) -> None:
        """
        Delete a user and all associated refresh tokens.

        Args:
            user_id: User UUID

        Raises:
            AppException: If user not found
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise AppException(
                status_code=404,
                error_code=ErrorCode.USER_NOT_FOUND,
                message="User not found",
                details=f"User with ID '{user_id}' does not exist",
                context={"user_id": str(user_id)}
            )

        try:
            # Delete user (refresh tokens cascade automatically)
            await self.repo.delete(user)
            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

    async def authenticate(self, email: str, password: str) -> User:
        """
        Authenticate user with email and password.

        If user is inactive (deactivated), reactivates the account on successful login.

        Args:
            email: User email
            password: Plain text password

        Returns:
            Authenticated user

        Raises:
            UnauthorizedException: If credentials invalid
        """
        user = await self.repo.get_by_email(email)

        # Verify user exists and password is correct
        if not user or not await verify_password(password, user.hashed_password):
            raise UnauthorizedException(
                message="Incorrect email or password",
                details="Invalid credentials provided"
            )

        # Reactivate user if they were deactivated
        if not user.is_active:
            try:
                user.is_active = True
                await self.repo.update(user)
                await self.db.commit()
                await self.db.refresh(user)
            except Exception:
                await self.db.rollback()
                raise

        return user

    async def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> None:
        """
        Change user password.

        Args:
            user_id: User UUID
            current_password: Current password for verification
            new_password: New password to set

        Raises:
            AppException: If user not found
            UnauthorizedException: If current password incorrect
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise AppException(
                status_code=404,
                error_code=ErrorCode.USER_NOT_FOUND,
                message="User not found",
                details=f"User with ID '{user_id}' does not exist",
                context={"user_id": str(user_id)}
            )

        # Verify current password
        if not await verify_password(current_password, user.hashed_password):
            raise UnauthorizedException(
                message="Current password is incorrect",
                details="The provided current password does not match"
            )

        try:
            # Set new password
            user.hashed_password = await hash_password(new_password)
            await self.repo.update(user)
            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

    async def create_refresh_token(self, user_id: UUID) -> tuple[str, str]:
        """
        Create access and refresh token pair for user.

        Args:
            user_id: User UUID

        Returns:
            Tuple of (access_token, refresh_token)
        """
        # Create JWT access token
        access_token = create_access_token(data={"sub": str(user_id)})

        # Generate refresh token
        refresh_token = generate_refresh_token()
        token_hash = await hash_refresh_token(refresh_token)
        token_lookup_hash = hash_token_for_lookup(refresh_token)

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        try:
            # Store refresh token in database
            db_refresh_token = RefreshToken(
                user_id=user_id,
                token_lookup_hash=token_lookup_hash,
                token_hash=token_hash,
                expires_at=expires_at,
                is_revoked=False,
            )
            self.db.add(db_refresh_token)
            await self.db.commit()

            return (access_token, refresh_token)

        except Exception:
            await self.db.rollback()
            raise

    async def refresh_access_token(self, refresh_token: str) -> str:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Plain refresh token

        Returns:
            New access token

        Raises:
            UnauthorizedException: If refresh token invalid or expired
        """
        from sqlalchemy import select

        # Calculate lookup hash for O(1) database query
        lookup_hash = hash_token_for_lookup(refresh_token)

        # Query for the specific token using indexed lookup hash
        stmt = select(RefreshToken).where(
            RefreshToken.token_lookup_hash == lookup_hash,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        )
        result = await self.db.execute(stmt)
        matched_token = result.scalar_one_or_none()

        # Verify with bcrypt for security (prevents collision attacks on SHA256)
        if not matched_token or not await verify_refresh_token(refresh_token, matched_token.token_hash):
            raise UnauthorizedException(
                message="Invalid or expired refresh token",
                details="The provided refresh token is invalid, expired, or has been revoked"
            )

        # Get user associated with the token
        user = await self.repo.get_by_id(matched_token.user_id)

        if not user or not user.is_active:
            raise UnauthorizedException(
                message="User not found or inactive",
                details="The user associated with this token does not exist or is inactive"
            )

        # Create new access token
        access_token = create_access_token(data={"sub": str(user.id)})

        return access_token

    async def revoke_refresh_token(self, user_id: UUID, refresh_token: str) -> None:
        """
        Revoke a refresh token (logout).

        Args:
            user_id: User UUID
            refresh_token: Plain refresh token to revoke

        Raises:
            AppException: If refresh token not found
        """
        from sqlalchemy import select

        # Calculate lookup hash for O(1) database query
        lookup_hash = hash_token_for_lookup(refresh_token)

        # Query for the specific token using indexed lookup hash
        stmt = select(RefreshToken).where(
            RefreshToken.token_lookup_hash == lookup_hash,
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        )
        result = await self.db.execute(stmt)
        matched_token = result.scalar_one_or_none()

        # Verify with bcrypt for security (prevents collision attacks on SHA256)
        if not matched_token or not await verify_refresh_token(refresh_token, matched_token.token_hash):
            raise AppException(
                status_code=404,
                error_code=ErrorCode.NOT_FOUND,
                message="Refresh token not found",
                details="The specified refresh token could not be found or is already revoked",
                context={"user_id": str(user_id)}
            )

        try:
            # Revoke the token
            matched_token.is_revoked = True
            matched_token.revoked_at = datetime.now(timezone.utc)
            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

    async def create_verification_token(self, user_id: UUID) -> str:
        """
        Create or update email verification token for user.

        Args:
            user_id: User UUID

        Returns:
            Verification token

        Raises:
            AppException: If user not found
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise AppException(
                status_code=404,
                error_code=ErrorCode.USER_NOT_FOUND,
                message="User not found",
                details=f"User with ID '{user_id}' does not exist",
                context={"user_id": str(user_id)}
            )

        try:
            # Generate new verification token
            token = generate_verification_token()
            expires_at = datetime.now(timezone.utc) + timedelta(
                hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
            )

            # Update user with verification token
            user.verification_token = token
            user.verification_token_expires_at = expires_at
            await self.repo.update(user)
            await self.db.commit()

            return token

        except Exception:
            await self.db.rollback()
            raise

    async def verify_email(self, token: str) -> UserRead:
        """
        Verify user email with token.

        Args:
            token: Verification token

        Returns:
            Verified user information

        Raises:
            ValidationException: If token invalid or expired
        """
        # Find user by verification token
        stmt = select(User).where(User.verification_token == token)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ValidationException(
                message="Invalid verification token",
                details="The provided verification token does not exist"
            )

        # Check if token expired
        if user.verification_token_expires_at is None or \
           user.verification_token_expires_at < datetime.now(timezone.utc):
            raise ValidationException(
                message="Verification token has expired",
                details="Please request a new verification email"
            )

        try:
            # Mark user as verified and clear token
            user.is_verified = True
            user.verification_token = None
            user.verification_token_expires_at = None
            await self.repo.update(user)
            await self.db.commit()
            await self.db.refresh(user)

            return UserRead(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                is_verified=user.is_verified,
                created_at=user.created_at,
            )

        except Exception:
            await self.db.rollback()
            raise

    async def request_password_reset(self, email: str) -> str | None:
        """
        Create password reset token and return it.

        Does NOT send email - that's handled by the endpoint.
        Always returns success even if user doesn't exist (security best practice).

        Args:
            email: User email address

        Returns:
            Reset token if user exists, None otherwise
        """
        user = await self.repo.get_by_email(email)
        if not user:
            # Don't reveal if user exists or not (security)
            return None

        try:
            # Generate reset token
            token = generate_verification_token()  # Same secure token generation
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour expiry

            # Update user with reset token
            user.reset_token = token
            user.reset_token_expires_at = expires_at
            await self.repo.update(user)
            await self.db.commit()

            return token

        except Exception:
            await self.db.rollback()
            raise

    async def reset_password(self, token: str, new_password: str) -> UserRead:
        """
        Reset user password with token.

        Args:
            token: Password reset token
            new_password: New password to set

        Returns:
            Updated user information

        Raises:
            ValidationException: If token invalid or expired
        """
        # Find user by reset token
        stmt = select(User).where(User.reset_token == token)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ValidationException(
                message="Invalid or expired reset token",
                details="The provided reset token does not exist or has already been used"
            )

        # Check if token expired
        if user.reset_token_expires_at is None or \
           user.reset_token_expires_at < datetime.now(timezone.utc):
            raise ValidationException(
                message="Reset token has expired",
                details="Please request a new password reset"
            )

        try:
            # Set new password and clear reset token
            user.hashed_password = await hash_password(new_password)
            user.reset_token = None
            user.reset_token_expires_at = None
            await self.repo.update(user)
            await self.db.commit()
            await self.db.refresh(user)

            return UserRead(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                is_superuser=user.is_superuser,
                is_verified=user.is_verified,
                created_at=user.created_at,
            )

        except Exception:
            await self.db.rollback()
            raise
