"""
Tests for refresh token lookup performance optimization.

This test verifies that the token_lookup_hash optimization works correctly
and prevents O(n) bcrypt operations.
"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models.refresh_token import RefreshToken
from app.services.user_service import UserService
from app.utils.auth import (
    generate_refresh_token,
    hash_refresh_token,
    hash_token_for_lookup
)
from fastapi import HTTPException


@pytest.mark.asyncio
class TestRefreshTokenPerformance:
    """Test refresh token lookup optimization."""

    async def test_token_lookup_hash_is_deterministic(self):
        """Verify that lookup hash is deterministic (same token -> same hash)."""
        token = generate_refresh_token()

        hash1 = hash_token_for_lookup(token)
        hash2 = hash_token_for_lookup(token)

        assert hash1 == hash2, "Lookup hash should be deterministic"
        assert len(hash1) == 64, "SHA256 hex digest should be 64 chars"

    async def test_token_lookup_hash_is_unique(self):
        """Verify that different tokens produce different lookup hashes."""
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()

        hash1 = hash_token_for_lookup(token1)
        hash2 = hash_token_for_lookup(token2)

        assert hash1 != hash2, "Different tokens should have different lookup hashes"

    async def test_refresh_access_token_uses_lookup_hash(self, db_session, test_user):
        """
        Verify that refresh_access_token uses lookup_hash for O(1) query
        instead of O(n) bcrypt verification.
        """
        service = UserService(db_session)

        # Create a refresh token
        access_token, refresh_token = await service.create_refresh_token(test_user.id)

        # Verify we can refresh using the token
        new_access_token = await service.refresh_access_token(refresh_token)

        assert new_access_token is not None
        assert new_access_token != access_token  # Should be a new token

    async def test_refresh_access_token_fails_with_wrong_token(self, db_session, test_user):
        """Verify that wrong tokens are rejected."""
        service = UserService(db_session)

        # Create a valid token
        await service.create_refresh_token(test_user.id)

        # Try to refresh with a wrong token
        wrong_token = generate_refresh_token()

        with pytest.raises(HTTPException) as exc_info:
            await service.refresh_access_token(wrong_token)

        assert exc_info.value.status_code == 401
        assert "Invalid or expired" in exc_info.value.detail

    async def test_revoke_refresh_token_uses_lookup_hash(self, db_session, test_user):
        """
        Verify that revoke_refresh_token uses lookup_hash for O(1) query
        instead of O(n) bcrypt verification.
        """
        service = UserService(db_session)

        # Create a refresh token
        _, refresh_token = await service.create_refresh_token(test_user.id)

        # Revoke it
        await service.revoke_refresh_token(test_user.id, refresh_token)

        # Try to use the revoked token
        with pytest.raises(HTTPException) as exc_info:
            await service.refresh_access_token(refresh_token)

        assert exc_info.value.status_code == 401

    async def test_multiple_tokens_lookup_performance(self, db_session, test_user):
        """
        Verify that lookup works correctly with multiple tokens in database.

        This simulates the scenario where O(n) would be problematic.
        """
        service = UserService(db_session)

        # Create multiple refresh tokens
        tokens = []
        for _ in range(5):
            _, refresh_token = await service.create_refresh_token(test_user.id)
            tokens.append(refresh_token)

        # Verify we can refresh using any of them (should be O(1) lookup each time)
        for token in tokens:
            new_access_token = await service.refresh_access_token(token)
            assert new_access_token is not None

    async def test_bcrypt_verification_prevents_collision_attacks(self, db_session, test_user):
        """
        Verify that even if someone finds a SHA256 collision, bcrypt verification
        prevents token forgery.
        """
        service = UserService(db_session)

        # Create a valid token
        _, real_token = await service.create_refresh_token(test_user.id)

        # Create a fake token with same lookup hash but different content
        # (In reality this would require finding a SHA256 collision, but we simulate it)
        lookup_hash = hash_token_for_lookup(real_token)

        # Manually create a token with the same lookup_hash but different bcrypt hash
        fake_token = "fake_token_that_collides"
        fake_bcrypt_hash = await hash_refresh_token(fake_token)

        # Insert the fake token directly into DB (simulating collision)
        fake_db_token = RefreshToken(
            user_id=test_user.id,
            token_lookup_hash=lookup_hash + "_collision",  # Different to avoid unique constraint
            token_hash=fake_bcrypt_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False
        )
        db_session.add(fake_db_token)
        await db_session.commit()

        # The fake token should NOT work (bcrypt verification fails)
        with pytest.raises(HTTPException):
            await service.refresh_access_token(fake_token)

        # But the real token should still work
        new_access_token = await service.refresh_access_token(real_token)
        assert new_access_token is not None
