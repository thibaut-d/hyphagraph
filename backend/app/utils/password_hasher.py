"""
Password hashing utilities using bcrypt.

Bcrypt operations are CPU-bound and run in a thread pool to avoid blocking
the async event loop during password hashing/verification.
"""
import asyncio
import logging
import bcrypt
from concurrent.futures import ThreadPoolExecutor
from app.config import settings

logger = logging.getLogger(__name__)


# Thread pool for CPU-bound bcrypt operations
# Prevents blocking the async event loop during password hashing
_bcrypt_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bcrypt")


class PasswordHasher:
    """
    Password hashing and verification using bcrypt.

    All operations run in a thread pool to avoid blocking the async event loop.

    Cost factor is configurable via BCRYPT_ROUNDS:
    - 10 = ~100ms (fast, for dev/test environments)
    - 12 = ~400ms (secure, for production)
    """

    def __init__(self, bcrypt_rounds: int = settings.BCRYPT_ROUNDS):
        """
        Initialize the password hasher.

        Args:
            bcrypt_rounds: Cost factor for bcrypt (default from settings)
        """
        self.bcrypt_rounds = bcrypt_rounds

    async def hash_password(self, password: str) -> str:
        """
        Hash a plain text password using bcrypt (async, runs in thread pool).

        Args:
            password: Plain text password

        Returns:
            Hashed password string (bcrypt hash)

        Note:
            Bcrypt has a 72-byte limit. Passwords are truncated to 72 bytes
            before hashing to prevent errors.
        """
        # Truncate to 72 bytes (bcrypt limit)
        password_bytes = password.encode('utf-8')[:72]

        # Run blocking bcrypt in thread pool
        def _hash() -> str:
            salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
            hashed = bcrypt.hashpw(password_bytes, salt)
            return hashed.decode('utf-8')

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_bcrypt_executor, _hash)

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against a hashed password (async, runs in thread pool).

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise

        Note:
            Truncates to 72 bytes to match hashing behavior.
        """
        # Truncate to 72 bytes (bcrypt limit)
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')

        # Run blocking bcrypt in thread pool
        def _check() -> bool:
            try:
                return bcrypt.checkpw(password_bytes, hashed_bytes)
            except Exception as exc:
                # Invalid hash format or other bcrypt error — treat as mismatch.
                # Log the exception type so corrupted hashes are diagnosable.
                logger.error("bcrypt.checkpw raised an unexpected error: %s", type(exc).__name__)
                return False

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_bcrypt_executor, _check)


# Singleton instance for convenience
password_hasher = PasswordHasher()


# Convenience functions for backwards compatibility
async def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt (async, runs in thread pool).

    Convenience function that uses the default password hasher.
    """
    return await password_hasher.hash_password(password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password (async, runs in thread pool).

    Convenience function that uses the default password hasher.
    """
    return await password_hasher.verify_password(plain_password, hashed_password)
