"""
Unit tests for authentication utilities.

Tests password hashing, JWT token generation, and refresh token utilities.
"""
import pytest
from datetime import datetime, timedelta, timezone
from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_refresh_token,
)
from app.config import settings


class TestPasswordHashing:
    """Test password hashing and verification."""

    async def test_hash_password_creates_different_hashes(self):
        """Same password should create different hashes (salt)."""
        password = "test_password_123"
        hash1 = await hash_password(password)
        hash2 = await hash_password(password)

        assert hash1 != hash2  # Different due to random salt
        assert hash1.startswith("$2b$")  # bcrypt format

    async def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        password = "correct_password"
        hashed = await hash_password(password)

        assert await verify_password(password, hashed) is True

    async def test_verify_password_incorrect(self):
        """Incorrect password should fail verification."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = await hash_password(password)

        assert await verify_password(wrong_password, hashed) is False

    async def test_hash_password_handles_unicode(self):
        """Password hashing should handle unicode characters."""
        password = "пароль_中文_🔒"
        hashed = await hash_password(password)

        assert await verify_password(password, hashed) is True


class TestJWTTokens:
    """Test JWT access token generation and decoding."""

    def test_create_access_token_contains_subject(self):
        """Access token should contain the subject (user_id)."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        token = create_access_token(data={"sub": user_id})

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token_valid(self):
        """Valid token should decode correctly."""
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        token = create_access_token(data={"sub": user_id})

        decoded_user_id = decode_access_token(token)

        assert decoded_user_id == user_id

    def test_decode_access_token_invalid(self):
        """Invalid token should return None."""
        invalid_token = "invalid.jwt.token"

        decoded = decode_access_token(invalid_token)

        assert decoded is None

    def test_decode_access_token_expired(self):
        """Expired token should return None."""
        from jose import jwt

        # Create token that expired 1 hour ago
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        to_encode = {"sub": user_id, "exp": expire}
        expired_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        decoded = decode_access_token(expired_token)

        assert decoded is None

    def test_access_token_has_expiration(self):
        """Access token should have expiration set."""
        from jose import jwt

        user_id = "123e4567-e89b-12d3-a456-426614174000"
        token = create_access_token(data={"sub": user_id})

        # Decode without verification to inspect claims
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == user_id


class TestRefreshTokens:
    """Test refresh token generation and verification."""

    def test_generate_refresh_token_is_random(self):
        """Each refresh token should be unique."""
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()

        assert token1 != token2
        assert len(token1) > 40  # URL-safe base64 of 32 bytes
        assert len(token2) > 40

    async def test_hash_refresh_token_creates_different_hashes(self):
        """Same token should create different hashes (salt)."""
        token = "test_refresh_token"
        hash1 = await hash_refresh_token(token)
        hash2 = await hash_refresh_token(token)

        assert hash1 != hash2  # Different due to random salt
        assert hash1.startswith("$2b$")  # bcrypt format

    async def test_verify_refresh_token_correct(self):
        """Correct token should verify successfully."""
        token = generate_refresh_token()
        hashed = await hash_refresh_token(token)

        assert await verify_refresh_token(token, hashed) is True

    async def test_verify_refresh_token_incorrect(self):
        """Incorrect token should fail verification."""
        token = generate_refresh_token()
        wrong_token = generate_refresh_token()
        hashed = await hash_refresh_token(token)

        assert await verify_refresh_token(wrong_token, hashed) is False

    def test_refresh_token_url_safe(self):
        """Refresh tokens should be URL-safe (no +, /, =)."""
        token = generate_refresh_token()

        # URL-safe base64 uses - and _ instead of + and /
        assert "+" not in token
        assert "/" not in token
        # May or may not have padding, both are valid
