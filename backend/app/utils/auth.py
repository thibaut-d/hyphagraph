"""
Authentication utilities facade.

This module is the **single import point** for all auth helpers used across the
codebase (user_service.py, user/tokens.py, dependencies/auth.py, tests, etc.).
It deliberately re-exports from three focused sub-modules so that callers never
need to know the internal layout:

- password_hasher:      bcrypt password hashing (async-safe via ThreadPoolExecutor)
- access_token_manager: JWT access-token signing and decoding (SECRET_KEY resolved
                        lazily at call time to support runtime key rotation)
- refresh_token_manager: opaque refresh-token generation, hashing, and verification

DO NOT import directly from these sub-modules in application code; always import
from ``app.utils.auth`` so that refactors to the internal layout stay transparent
to all callers.
"""
# Re-export all public functions from focused modules
from app.utils.password_hasher import (
    hash_password,
    verify_password,
    password_hasher,
    PasswordHasher,
)
from app.utils.access_token_manager import (
    create_access_token,
    decode_access_token,
    decode_access_token_payload,
    access_token_manager,
    AccessTokenManager,
)
from app.utils.refresh_token_manager import (
    generate_refresh_token,
    hash_token_for_lookup,
    hash_refresh_token,
    verify_refresh_token,
    refresh_token_manager,
    RefreshTokenManager,
)

# Export all public names
__all__ = [
    # Password operations
    "hash_password",
    "verify_password",
    "password_hasher",
    "PasswordHasher",
    # Access token operations
    "create_access_token",
    "decode_access_token",
    "decode_access_token_payload",
    "access_token_manager",
    "AccessTokenManager",
    # Refresh token operations
    "generate_refresh_token",
    "hash_token_for_lookup",
    "hash_refresh_token",
    "verify_refresh_token",
    "refresh_token_manager",
    "RefreshTokenManager",
]
