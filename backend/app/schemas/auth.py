"""
Authentication schemas for request/response validation.
"""
from uuid import UUID
from datetime import datetime
from pydantic import EmailStr, Field
from app.schemas.base import Schema


class UserRegister(Schema):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters")


class UserLogin(Schema):
    """Schema for user login (alternative to OAuth2PasswordRequestForm)."""
    email: EmailStr
    password: str


class Token(Schema):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenPair(Schema):
    """JWT token pair response (access + refresh)."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(Schema):
    """Request schema for refresh token endpoint."""
    refresh_token: str


class TokenData(Schema):
    """Token payload data."""
    user_id: UUID | None = None


class UserRead(Schema):
    """Schema for reading user information."""
    id: UUID
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class UserUpdate(Schema):
    """Schema for updating user information."""
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8)
    is_active: bool | None = None


class ChangePassword(Schema):
    """Schema for changing password."""
    current_password: str = Field(min_length=1, description="Current password for verification")
    new_password: str = Field(min_length=8, description="New password must be at least 8 characters")


class VerifyEmail(Schema):
    """Schema for email verification."""
    token: str = Field(min_length=1, description="Email verification token")


class ResendVerificationEmail(Schema):
    """Schema for resending verification email."""
    email: EmailStr = Field(description="Email address to resend verification to")


class RequestPasswordReset(Schema):
    """Schema for requesting password reset."""
    email: EmailStr = Field(description="Email address to send password reset link")


class ResetPassword(Schema):
    """Schema for resetting password with token."""
    token: str = Field(min_length=1, description="Password reset token")
    new_password: str = Field(min_length=8, description="New password must be at least 8 characters")
