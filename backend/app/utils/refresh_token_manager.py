"""
Refresh token management.

Handles generation, hashing, and verification of refresh tokens.
Uses bcrypt for secure storage and SHA256 for fast lookup indexing.
"""
import asyncio
import hashlib
import secrets
import bcrypt
from concurrent.futures import ThreadPoolExecutor
from app.config import settings


# Thread pool for CPU-bound bcrypt operations
# Shared with password hashing to limit total threads
_bcrypt_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bcrypt")


class RefreshTokenManager:
    """
    Refresh token generation, hashing, and verification.

    Uses bcrypt for secure storage (consistent with password hashing) and
    SHA256 for fast database lookup indexing.

    All bcrypt operations run in a thread pool to avoid blocking the async event loop.
    """

    def __init__(self, bcrypt_rounds: int = settings.BCRYPT_ROUNDS):
        """
        Initialize the refresh token manager.

        Args:
            bcrypt_rounds: Cost factor for bcrypt (default from settings)
        """
        self.bcrypt_rounds = bcrypt_rounds

    def generate_refresh_token(self) -> str:
        """
        Generate a cryptographically secure random refresh token.

        Returns:
            URL-safe random token string (32 bytes = 43 characters base64)
        """
        return secrets.token_urlsafe(32)

    def hash_token_for_lookup(self, token: str) -> str:
        """
        Create a deterministic SHA256 hash of a token for fast database lookup.

        This is NOT for security - it's for indexing. The bcrypt hash is used
        for actual verification.

        Args:
            token: Plain refresh token string

        Returns:
            SHA256 hex digest (64 characters)
        """
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    async def hash_refresh_token(self, token: str) -> str:
        """
        Hash a refresh token for secure storage in the database (async, runs in thread pool).

        Uses bcrypt for consistency with password hashing.

        Args:
            token: Plain refresh token string

        Returns:
            Hashed token string (bcrypt hash)

        Note:
            Bcrypt has a 72-byte limit. Tokens are truncated to 72 bytes
            before hashing to prevent errors.

            Uses configurable BCRYPT_ROUNDS (same as passwords).
        """
        # Truncate to 72 bytes (bcrypt limit)
        token_bytes = token.encode('utf-8')[:72]

        # Run blocking bcrypt in thread pool
        def _hash() -> str:
            salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
            hashed = bcrypt.hashpw(token_bytes, salt)
            return hashed.decode('utf-8')

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_bcrypt_executor, _hash)

    async def verify_refresh_token(self, plain_token: str, hashed_token: str) -> bool:
        """
        Verify a plain refresh token against a hashed token (async, runs in thread pool).

        Args:
            plain_token: Plain refresh token to verify
            hashed_token: Hashed token to compare against

        Returns:
            True if token matches, False otherwise

        Note:
            Truncates to 72 bytes to match hashing behavior.
        """
        # Truncate to 72 bytes (bcrypt limit)
        token_bytes = plain_token.encode('utf-8')[:72]
        hashed_bytes = hashed_token.encode('utf-8')

        # Run blocking bcrypt in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _bcrypt_executor,
            lambda: bcrypt.checkpw(token_bytes, hashed_bytes)
        )


# Singleton instance for convenience
refresh_token_manager = RefreshTokenManager()


# Convenience functions for backwards compatibility
def generate_refresh_token() -> str:
    """
    Generate a cryptographically secure random refresh token.

    Convenience function that uses the default refresh token manager.
    """
    return refresh_token_manager.generate_refresh_token()


def hash_token_for_lookup(token: str) -> str:
    """
    Create a deterministic SHA256 hash of a token for fast database lookup.

    Convenience function that uses the default refresh token manager.
    """
    return refresh_token_manager.hash_token_for_lookup(token)


async def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for secure storage in the database (async, runs in thread pool).

    Convenience function that uses the default refresh token manager.
    """
    return await refresh_token_manager.hash_refresh_token(token)


async def verify_refresh_token(plain_token: str, hashed_token: str) -> bool:
    """
    Verify a plain refresh token against a hashed token (async, runs in thread pool).

    Convenience function that uses the default refresh token manager.
    """
    return await refresh_token_manager.verify_refresh_token(plain_token, hashed_token)
