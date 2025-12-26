from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from uuid import UUID
from datetime import datetime, timedelta

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
    verify_refresh_token
)
from app.utils.email import (
    generate_verification_token,
    send_verification_email,
    send_password_reset_email,
)
from app.config import settings


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
            HTTPException 400: If email already registered
        """
        # Check if email already exists
        existing_user = await self.repo.get_by_email(payload.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password
        hashed_password = hash_password(payload.password)

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
            HTTPException 404: If user not found
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return UserRead(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
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
            HTTPException 404: If user not found
            HTTPException 400: If email already in use
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        try:
            # Update email if provided
            if payload.email is not None:
                # Check if email is already in use by another user
                existing = await self.repo.get_by_email(payload.email)
                if existing and existing.id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already in use"
                    )
                user.email = payload.email

            # Update password if provided
            if payload.password is not None:
                user.hashed_password = hash_password(payload.password)

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
                created_at=user.created_at,
            )

        except HTTPException:
            await self.db.rollback()
            raise
        except Exception:
            await self.db.rollback()
            raise

    async def delete(self, user_id: UUID) -> None:
        """
        Delete a user and all associated refresh tokens.

        Args:
            user_id: User UUID

        Raises:
            HTTPException 404: If user not found
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
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

        Args:
            email: User email
            password: Plain text password

        Returns:
            Authenticated user

        Raises:
            HTTPException 401: If credentials invalid
            HTTPException 403: If user inactive
        """
        user = await self.repo.get_by_email(email)

        # Verify user exists and password is correct
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user account"
            )

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
            HTTPException 404: If user not found
            HTTPException 401: If current password incorrect
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify current password
        if not verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )

        try:
            # Set new password
            user.hashed_password = hash_password(new_password)
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
        token_hash = hash_refresh_token(refresh_token)

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        try:
            # Store refresh token in database
            db_refresh_token = RefreshToken(
                user_id=user_id,
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
            HTTPException 401: If refresh token invalid or expired
        """
        from sqlalchemy import select

        # Query all active, non-expired refresh tokens
        stmt = select(RefreshToken).where(
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        )
        result = await self.db.execute(stmt)
        all_tokens = result.scalars().all()

        # Find matching token by verifying hash
        matched_token = None
        for token in all_tokens:
            if verify_refresh_token(refresh_token, token.token_hash):
                matched_token = token
                break

        if not matched_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user associated with the token
        user = await self.repo.get_by_id(matched_token.user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
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
            HTTPException 404: If refresh token not found
        """
        from sqlalchemy import select

        # Find active refresh tokens for this user
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        )
        result = await self.db.execute(stmt)
        all_tokens = result.scalars().all()

        # Find matching token by verifying hash
        matched_token = None
        for token in all_tokens:
            if verify_refresh_token(refresh_token, token.token_hash):
                matched_token = token
                break

        if not matched_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Refresh token not found"
            )

        try:
            # Revoke the token
            matched_token.is_revoked = True
            matched_token.revoked_at = datetime.utcnow()
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
            HTTPException 404: If user not found
        """
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        try:
            # Generate new verification token
            token = generate_verification_token()
            expires_at = datetime.utcnow() + timedelta(
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
            HTTPException 400: If token invalid or expired
        """
        # Find user by verification token
        stmt = select(User).where(User.verification_token == token)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )

        # Check if token expired
        if user.verification_token_expires_at is None or \
           user.verification_token_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired"
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
            expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry

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
            HTTPException 400: If token invalid or expired
        """
        # Find user by reset token
        stmt = select(User).where(User.reset_token == token)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Check if token expired
        if user.reset_token_expires_at is None or \
           user.reset_token_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )

        try:
            # Set new password and clear reset token
            user.hashed_password = hash_password(new_password)
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
                created_at=user.created_at,
            )

        except Exception:
            await self.db.rollback()
            raise
