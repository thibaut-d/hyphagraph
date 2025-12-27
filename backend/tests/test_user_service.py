"""
Unit tests for UserService.

Tests user registration, authentication, password management, and token operations.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import HTTPException

from app.services.user_service import UserService
from app.schemas.auth import UserRegister, UserUpdate
from app.models.user import User
from app.config import settings


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_user_repo():
    """Mock UserRepository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def user_service(mock_db, mock_user_repo):
    """UserService instance with mocked dependencies."""
    service = UserService(mock_db)
    service.repo = mock_user_repo
    return service


@pytest.fixture
def sample_user():
    """Sample user model."""
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="$2b$12$hashed_password_here",
        is_active=True,
        is_superuser=False,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
    )


class TestUserCreation:
    """Test user registration and creation."""

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repo, mock_db):
        """Successfully create a new user."""
        mock_user_repo.get_by_email.return_value = None  # Email doesn't exist

        # Mock refresh to populate id, created_at, and is_verified
        def mock_refresh_side_effect(user):
            user.id = uuid4()
            user.created_at = datetime.now(timezone.utc)
            user.is_verified = False

        mock_db.refresh.side_effect = mock_refresh_side_effect

        payload = UserRegister(email="new@example.com", password="password123")

        with patch("app.services.user_service.hash_password") as mock_hash:
            mock_hash.return_value = "hashed_password"
            result = await user_service.create(payload)

        assert result.email == "new@example.com"
        assert not result.is_superuser
        assert result.id is not None
        assert result.created_at is not None
        mock_user_repo.create.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, user_service, mock_user_repo, sample_user):
        """Creating user with existing email should fail."""
        mock_user_repo.get_by_email.return_value = sample_user

        payload = UserRegister(email="test@example.com", password="password123")

        with pytest.raises(HTTPException) as exc_info:
            await user_service.create(payload)

        assert exc_info.value.status_code == 400
        assert "already registered" in exc_info.value.detail.lower()


class TestAuthentication:
    """Test user authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_success(self, user_service, mock_user_repo, sample_user):
        """Successful authentication with correct credentials."""
        mock_user_repo.get_by_email.return_value = sample_user

        with patch("app.services.user_service.verify_password") as mock_verify:
            mock_verify.return_value = True
            result = await user_service.authenticate("test@example.com", "correct_password")

        assert result.id == sample_user.id
        assert result.email == sample_user.email

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, user_service, mock_user_repo, sample_user):
        """Authentication with wrong password should fail."""
        mock_user_repo.get_by_email.return_value = sample_user

        with patch("app.services.user_service.verify_password") as mock_verify:
            mock_verify.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await user_service.authenticate("test@example.com", "wrong_password")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, user_service, mock_user_repo):
        """Authentication with non-existent user should fail."""
        mock_user_repo.get_by_email.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await user_service.authenticate("nonexistent@example.com", "password")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, user_service, mock_user_repo, sample_user, mock_db):
        """Authentication with inactive user should reactivate the account."""
        sample_user.is_active = False
        mock_user_repo.get_by_email.return_value = sample_user

        with patch("app.services.user_service.verify_password") as mock_verify:
            mock_verify.return_value = True

            result = await user_service.authenticate("test@example.com", "password")

        # User should be reactivated
        assert result.is_active == True
        assert mock_db.commit.call_count == 1


class TestPasswordManagement:
    """Test password change and reset operations."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, user_service, mock_user_repo, sample_user, mock_db):
        """Successfully change password with correct current password."""
        mock_user_repo.get_by_id.return_value = sample_user

        with patch("app.services.user_service.verify_password") as mock_verify, \
             patch("app.services.user_service.hash_password") as mock_hash:
            mock_verify.return_value = True
            mock_hash.return_value = "new_hashed_password"

            await user_service.change_password(
                sample_user.id,
                "current_password",
                "new_password123"
            )

        mock_db.commit.assert_called_once()
        mock_user_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, user_service, mock_user_repo, sample_user):
        """Changing password with wrong current password should fail."""
        mock_user_repo.get_by_id.return_value = sample_user

        with patch("app.services.user_service.verify_password") as mock_verify:
            mock_verify.return_value = False

            with pytest.raises(HTTPException) as exc_info:
                await user_service.change_password(
                    sample_user.id,
                    "wrong_password",
                    "new_password123"
                )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_request_password_reset_existing_user(
        self, user_service, mock_user_repo, sample_user, mock_db
    ):
        """Requesting password reset for existing user returns token."""
        mock_user_repo.get_by_email.return_value = sample_user

        with patch("app.services.user_service.generate_verification_token") as mock_gen:
            mock_gen.return_value = "reset_token_123"
            token = await user_service.request_password_reset("test@example.com")

        assert token == "reset_token_123"
        assert sample_user.reset_token == "reset_token_123"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_user(self, user_service, mock_user_repo):
        """Requesting reset for non-existent user returns None (security)."""
        mock_user_repo.get_by_email.return_value = None

        token = await user_service.request_password_reset("nonexistent@example.com")

        assert token is None


class TestEmailVerification:
    """Test email verification token operations."""

    @pytest.mark.asyncio
    async def test_create_verification_token(
        self, user_service, mock_user_repo, sample_user, mock_db
    ):
        """Creating verification token should generate and store token."""
        mock_user_repo.get_by_id.return_value = sample_user

        with patch("app.services.user_service.generate_verification_token") as mock_gen:
            mock_gen.return_value = "verification_token_123"
            token = await user_service.create_verification_token(sample_user.id)

        assert token == "verification_token_123"
        assert sample_user.verification_token == "verification_token_123"
        assert sample_user.verification_token_expires_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_email_valid_token(self, user_service, mock_db, sample_user):
        """Verifying email with valid token should succeed."""
        sample_user.verification_token = "valid_token"
        sample_user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await user_service.verify_email("valid_token")

        assert result.email == sample_user.email
        assert sample_user.is_verified is True
        assert sample_user.verification_token is None

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(self, user_service, mock_db, sample_user):
        """Verifying email with expired token should fail."""
        sample_user.verification_token = "expired_token"
        sample_user.verification_token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await user_service.verify_email("expired_token")

        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail.lower()


class TestRefreshTokens:
    """Test refresh token creation and usage."""

    @pytest.mark.asyncio
    async def test_create_refresh_token(self, user_service, mock_db):
        """Creating refresh token should return token pair."""
        user_id = uuid4()

        with patch("app.services.user_service.create_access_token") as mock_access, \
             patch("app.services.user_service.generate_refresh_token") as mock_refresh, \
             patch("app.services.user_service.hash_refresh_token") as mock_hash:
            mock_access.return_value = "access_token_123"
            mock_refresh.return_value = "refresh_token_123"
            mock_hash.return_value = "hashed_refresh_token"

            access_token, refresh_token = await user_service.create_refresh_token(user_id)

        assert access_token == "access_token_123"
        assert refresh_token == "refresh_token_123"
        mock_db.commit.assert_called_once()
