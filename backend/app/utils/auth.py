"""
Authentication utilities for JWT token handling and password hashing.

Uses python-jose for JWT and bcrypt for password hashing.
NO third-party auth frameworks.

Bcrypt operations are CPU-bound and run in a thread pool to avoid blocking
the async event loop during password hashing/verification.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4
import secrets
import bcrypt
import asyncio
from concurrent.futures import ThreadPoolExecutor
from jose import JWTError, jwt
from app.config import settings


# Thread pool for CPU-bound bcrypt operations
# Prevents blocking the async event loop during password hashing
_bcrypt_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bcrypt")


async def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt (async, runs in thread pool).

    Args:
        password: Plain text password

    Returns:
        Hashed password string (bcrypt hash)

    Note:
        Bcrypt has a 72-byte limit. Passwords are truncated to 72 bytes
        before hashing to prevent errors.

        Cost factor is configurable via BCRYPT_ROUNDS:
        - 10 = ~100ms (fast, for dev/test environments)
        - 12 = ~400ms (secure, for production)

        This function runs in a thread pool to avoid blocking the event loop.
    """
    # Truncate to 72 bytes (bcrypt limit)
    password_bytes = password.encode('utf-8')[:72]

    # Run blocking bcrypt in thread pool
    def _hash():
        salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_bcrypt_executor, _hash)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password (async, runs in thread pool).

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise

    Note:
        Truncates to 72 bytes to match hashing behavior.
        This function runs in a thread pool to avoid blocking the event loop.
    """
    # Truncate to 72 bytes (bcrypt limit)
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')

    # Run blocking bcrypt in thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _bcrypt_executor,
        lambda: bcrypt.checkpw(password_bytes, hashed_bytes)
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token (typically {"sub": user_id})
        expires_delta: Optional expiration time delta (default: 30 minutes)

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Encode JWT
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[str]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        User ID (subject) from token if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        return user_id
    except JWTError:
        return None


def generate_refresh_token() -> str:
    """
    Generate a cryptographically secure random refresh token.

    Returns:
        URL-safe random token string (32 bytes = 43 characters base64)
    """
    return secrets.token_urlsafe(32)


async def hash_refresh_token(token: str) -> str:
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
        This function runs in a thread pool to avoid blocking the event loop.
    """
    # Truncate to 72 bytes (bcrypt limit)
    token_bytes = token.encode('utf-8')[:72]

    # Run blocking bcrypt in thread pool
    def _hash():
        salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(token_bytes, salt)
        return hashed.decode('utf-8')

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_bcrypt_executor, _hash)


async def verify_refresh_token(plain_token: str, hashed_token: str) -> bool:
    """
    Verify a plain refresh token against a hashed token (async, runs in thread pool).

    Args:
        plain_token: Plain refresh token to verify
        hashed_token: Hashed token to compare against

    Returns:
        True if token matches, False otherwise

    Note:
        Truncates to 72 bytes to match hashing behavior.
        This function runs in a thread pool to avoid blocking the event loop.
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
