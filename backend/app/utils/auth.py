"""
Authentication utilities facade.

This module provides a unified interface for authentication operations.
Implementation is split into focused modules:
- password_hasher: Password hashing with bcrypt
- access_token_manager: JWT access token management
- refresh_token_manager: Refresh token generation and verification

All functions maintain the same interface for backwards compatibility.
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
