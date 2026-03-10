"""
JWT access token management.

Uses python-jose for JWT encoding/decoding.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from app.config import settings


class AccessTokenManager:
    """
    JWT access token creation and validation.

    Handles encoding/decoding of JWT tokens with configurable expiration.
    """

    def __init__(
        self,
        secret_key: str = settings.SECRET_KEY,
        algorithm: str = settings.ALGORITHM,
        expire_minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    ):
        """
        Initialize the access token manager.

        Args:
            secret_key: Secret key for JWT signing (default from settings)
            algorithm: JWT algorithm (default from settings)
            expire_minutes: Token expiration in minutes (default from settings)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: Payload data to encode in the token (typically {"sub": user_id})
            expires_delta: Optional expiration time delta (default: from settings)

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()

        # Set expiration time
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.expire_minutes)

        to_encode.update({"exp": expire})

        # Encode JWT
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm
        )

        return encoded_jwt

    def decode_access_token(self, token: str) -> Optional[str]:
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
                self.secret_key,
                algorithms=[self.algorithm]
            )
            user_id: str = payload.get("sub")
            return user_id
        except JWTError:
            return None


# Singleton instance for convenience
access_token_manager = AccessTokenManager()


# Convenience functions for backwards compatibility
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Convenience function that uses the default access token manager.
    """
    return access_token_manager.create_access_token(data, expires_delta)


def decode_access_token(token: str) -> Optional[str]:
    """
    Decode and validate a JWT access token.

    Convenience function that uses the default access token manager.
    """
    return access_token_manager.decode_access_token(token)
