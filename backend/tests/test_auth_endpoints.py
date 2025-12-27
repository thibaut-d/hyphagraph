"""
Integration tests for authentication endpoints.

Tests the full authentication flow including registration, login,
token management, password reset, and email verification.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import status
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.user import User
from app.schemas.auth import UserRegister


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def sample_user():
    """Sample user model."""
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="$2b$12$hashed_password_here",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_tokens():
    """Sample access and refresh tokens."""
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
        "refresh_token": "refresh_token_123456",
    }


class TestRegistrationEndpoint:
    """Test /auth/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self):
        """Successfully register a new user."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                # Mock successful creation
                new_user = User(
                    id=uuid4(),
                    email="newuser@example.com",
                    is_active=True,
                    is_superuser=False,
                    is_verified=False,
                    created_at=datetime.now(timezone.utc),
                )
                mock_service.create.return_value = new_user
                mock_service.create_verification_token.return_value = "token123"

                response = await client.post(
                    "/api/auth/register",
                    json={"email": "newuser@example.com", "password": "password123"}
                )

                assert response.status_code == status.HTTP_201_CREATED
                data = response.json()
                assert data["email"] == "newuser@example.com"
                assert "password" not in data
                assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self):
        """Registration with existing email should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                # Mock duplicate email error
                from fastapi import HTTPException
                mock_service.create.side_effect = HTTPException(
                    status_code=400,
                    detail="Email already registered"
                )

                response = await client.post(
                    "/api/auth/register",
                    json={"email": "existing@example.com", "password": "password123"}
                )

                assert response.status_code == status.HTTP_400_BAD_REQUEST
                assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_email(self):
        """Registration with invalid email should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/auth/register",
                json={"email": "not-an-email", "password": "password123"}
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @pytest.mark.asyncio
    async def test_register_weak_password(self):
        """Registration with weak password should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/auth/register",
                json={"email": "test@example.com", "password": "123"}
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestLoginEndpoint:
    """Test /auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, sample_user):
        """Successfully login with correct credentials."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                # Mock successful authentication
                mock_service.authenticate.return_value = sample_user
                mock_service.create_refresh_token.return_value = (
                    "access_token_123",
                    "refresh_token_456"
                )

                response = await client.post(
                    "/api/auth/login",
                    data={"username": "test@example.com", "password": "password123"}
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        """Login with wrong password should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                # Mock authentication failure
                from fastapi import HTTPException
                mock_service.authenticate.side_effect = HTTPException(
                    status_code=401,
                    detail="Incorrect email or password"
                )

                response = await client.post(
                    "/api/auth/login",
                    data={"username": "test@example.com", "password": "wrongpassword"}
                )

                assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self):
        """Login with non-existent user should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                # Mock authentication failure
                from fastapi import HTTPException
                mock_service.authenticate.side_effect = HTTPException(
                    status_code=401,
                    detail="Incorrect email or password"
                )

                response = await client.post(
                    "/api/auth/login",
                    data={"username": "nonexistent@example.com", "password": "password"}
                )

                assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetCurrentUser:
    """Test /auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, sample_user):
        """Successfully get current user with valid token."""
        from app.dependencies.auth import get_current_user

        async def override_get_current_user():
            return sample_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(
                    "/api/auth/me",
                    headers={"Authorization": "Bearer valid_token"}
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["email"] == sample_user.email
                assert "password" not in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self):
        """Get current user without token should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/auth/me")

            assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestRefreshToken:
    """Test /auth/refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """Successfully refresh access token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                mock_service.refresh_access_token.return_value = "new_access_token"

                response = await client.post(
                    "/api/auth/refresh",
                    json={"refresh_token": "valid_refresh_token"}
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["access_token"] == "new_access_token"
                assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self):
        """Refresh with invalid token should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                from fastapi import HTTPException
                mock_service.refresh_access_token.side_effect = HTTPException(
                    status_code=401,
                    detail="Invalid refresh token"
                )

                response = await client.post(
                    "/api/auth/refresh",
                    json={"refresh_token": "invalid_token"}
                )

                assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    """Test /auth/logout endpoint."""

    @pytest.mark.asyncio
    async def test_logout_success(self, sample_user):
        """Successfully logout and revoke refresh token."""
        from app.dependencies.auth import get_current_user

        async def override_get_current_user():
            return sample_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.auth.UserService") as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service

                    response = await client.post(
                        "/api/auth/logout",
                        json={"refresh_token": "token_to_revoke"},
                        headers={"Authorization": "Bearer valid_token"}
                    )

                    assert response.status_code == status.HTTP_204_NO_CONTENT
                    mock_service.revoke_refresh_token.assert_called_once()
        finally:
            app.dependency_overrides.clear()


class TestChangePassword:
    """Test /auth/change-password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, sample_user):
        """Successfully change password."""
        from app.dependencies.auth import get_current_user

        async def override_get_current_user():
            return sample_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.auth.UserService") as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service

                    response = await client.post(
                        "/api/auth/change-password",
                        json={
                            "current_password": "oldpassword",
                            "new_password": "newpassword123"
                        },
                        headers={"Authorization": "Bearer valid_token"}
                    )

                    assert response.status_code == status.HTTP_204_NO_CONTENT
                    mock_service.change_password.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, sample_user):
        """Change password with wrong current password should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.dependencies.auth.get_current_user") as mock_get_user, \
                 patch("app.api.auth.UserService") as mock_service_class:
                mock_get_user.return_value = sample_user
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                from fastapi import HTTPException
                mock_service.change_password.side_effect = HTTPException(
                    status_code=401,
                    detail="Current password is incorrect"
                )

                response = await client.post(
                    "/api/auth/change-password",
                    json={
                        "current_password": "wrongpassword",
                        "new_password": "newpassword123"
                    },
                    headers={"Authorization": "Bearer valid_token"}
                )

                assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestEmailVerification:
    """Test email verification endpoints."""

    @pytest.mark.asyncio
    async def test_verify_email_success(self):
        """Successfully verify email with valid token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                verified_user = User(
                    id=uuid4(),
                    email="test@example.com",
                    is_verified=True,
                    is_active=True,
                    is_superuser=False,
                    created_at=datetime.now(timezone.utc),
                )
                from app.schemas.auth import UserRead
                mock_service.verify_email.return_value = UserRead(
                    id=verified_user.id,
                    email=verified_user.email,
                    is_active=verified_user.is_active,
                    is_superuser=verified_user.is_superuser,
                    is_verified=verified_user.is_verified,
                    created_at=verified_user.created_at,
                )

                response = await client.post(
                    "/api/auth/verify-email",
                    json={"token": "valid_verification_token"}
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["email"] == verified_user.email

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(self):
        """Verify email with expired token should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                from fastapi import HTTPException
                mock_service.verify_email.side_effect = HTTPException(
                    status_code=400,
                    detail="Verification token has expired"
                )

                response = await client.post(
                    "/api/auth/verify-email",
                    json={"token": "expired_token"}
                )

                assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_resend_verification_success(self):
        """Successfully resend verification email."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class, \
                 patch("app.utils.email.send_verification_email", AsyncMock()) as mock_send:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                unverified_user = User(
                    id=uuid4(),
                    email="test@example.com",
                    is_verified=False,
                    is_active=True,
                    is_superuser=False,
                    created_at=datetime.now(timezone.utc),
                )
                from app.schemas.auth import UserRead
                mock_service.get_by_email.return_value = UserRead(
                    id=unverified_user.id,
                    email=unverified_user.email,
                    is_active=unverified_user.is_active,
                    is_superuser=unverified_user.is_superuser,
                    is_verified=unverified_user.is_verified,
                    created_at=unverified_user.created_at,
                )
                mock_service.create_verification_token.return_value = "new_token"

                response = await client.post(
                    "/api/auth/resend-verification",
                    json={"email": "test@example.com"}
                )

                assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_resend_verification_already_verified(self):
        """Resend verification for already verified user should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                verified_user = User(
                    id=uuid4(),
                    email="test@example.com",
                    is_verified=True,
                    is_active=True,
                    is_superuser=False,
                    created_at=datetime.now(timezone.utc),
                )
                from app.schemas.auth import UserRead
                # Mock is_verified check - need to return actual User object
                user_obj = MagicMock()
                user_obj.is_verified = True
                mock_service.get_by_email.return_value = user_obj

                response = await client.post(
                    "/api/auth/resend-verification",
                    json={"email": "test@example.com"}
                )

                assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestPasswordReset:
    """Test password reset endpoints."""

    @pytest.mark.asyncio
    async def test_request_password_reset_success(self):
        """Successfully request password reset."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class, \
                 patch("app.utils.email.send_password_reset_email", AsyncMock()) as mock_send:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                mock_service.request_password_reset.return_value = "reset_token_123"

                response = await client.post(
                    "/api/auth/request-password-reset",
                    json={"email": "test@example.com"}
                )

                # Always returns success to prevent email enumeration
                assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_user(self):
        """Request reset for non-existent user returns success (security)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service
                mock_service.request_password_reset.return_value = None

                response = await client.post(
                    "/api/auth/request-password-reset",
                    json={"email": "nonexistent@example.com"}
                )

                # Still returns success to prevent email enumeration
                assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_reset_password_success(self):
        """Successfully reset password with valid token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                reset_user = User(
                    id=uuid4(),
                    email="test@example.com",
                    is_active=True,
                    is_superuser=False,
                    is_verified=True,
                    created_at=datetime.now(timezone.utc),
                )
                from app.schemas.auth import UserRead
                mock_service.reset_password.return_value = UserRead(
                    id=reset_user.id,
                    email=reset_user.email,
                    is_active=reset_user.is_active,
                    is_superuser=reset_user.is_superuser,
                    is_verified=reset_user.is_verified,
                    created_at=reset_user.created_at,
                )

                response = await client.post(
                    "/api/auth/reset-password",
                    json={
                        "token": "valid_reset_token",
                        "new_password": "newpassword123"
                    }
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["email"] == reset_user.email

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(self):
        """Reset password with expired token should fail."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            with patch("app.api.auth.UserService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service_class.return_value = mock_service

                from fastapi import HTTPException
                mock_service.reset_password.side_effect = HTTPException(
                    status_code=400,
                    detail="Password reset token has expired"
                )

                response = await client.post(
                    "/api/auth/reset-password",
                    json={
                        "token": "expired_token",
                        "new_password": "newpassword123"
                    }
                )

                assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAccountDeletion:
    """Test /auth/me DELETE endpoint."""

    @pytest.mark.asyncio
    async def test_delete_account_success(self, sample_user):
        """Successfully delete user account."""
        from app.dependencies.auth import get_current_user

        async def override_get_current_user():
            return sample_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.auth.UserService") as mock_service_class:
                    mock_service = AsyncMock()
                    mock_service_class.return_value = mock_service

                    response = await client.delete(
                        "/api/auth/me",
                        headers={"Authorization": "Bearer valid_token"}
                    )

                    assert response.status_code == status.HTTP_204_NO_CONTENT
                    mock_service.delete.assert_called_once_with(sample_user.id)
        finally:
            app.dependency_overrides.clear()
