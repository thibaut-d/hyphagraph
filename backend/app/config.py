from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    # Global
    ENV: str = "development"
    PROJECT_NAME: str = "hyphagraph"
    LOG_LEVEL: str = "info"

    # Database
    DATABASE_URL: str

    # Security / Authentication
    SECRET_KEY: str = "change-me"  # MUST be set in production via environment variable
    ALGORITHM: str = "HS256"  # JWT signing algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # JWT token expiration (30 minutes)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh token expiration (7 days)

    # Admin User (created automatically on startup)
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "changeme123"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True  # Enable/disable rate limiting globally
    RATE_LIMIT_PER_MINUTE: int = 60  # General API rate limit (requests per minute)
    AUTH_RATE_LIMIT_PER_MINUTE: int = 5  # Auth endpoints rate limit (login, register, etc.)

    # Email Configuration
    EMAIL_ENABLED: bool = False  # Enable/disable email sending
    EMAIL_FROM: str = "noreply@example.com"  # Sender email address
    EMAIL_FROM_NAME: str = "HyphaGraph"  # Sender name

    # SMTP Configuration (for SMTP-based email)
    SMTP_HOST: str | None = None  # SMTP server host
    SMTP_PORT: int = 587  # SMTP server port (587 for TLS, 465 for SSL)
    SMTP_USER: str | None = None  # SMTP username
    SMTP_PASSWORD: str | None = None  # SMTP password
    SMTP_TLS: bool = True  # Use TLS (STARTTLS)

    # Frontend URL (for email links)
    FRONTEND_URL: str = "http://localhost:3000"  # Frontend base URL for verification links

    # Email Verification
    EMAIL_VERIFICATION_REQUIRED: bool = False  # Require email verification for new users
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24  # Verification token expiry (24 hours)

    # Inference Engine
    INFERENCE_MODEL_VERSION: str = "v1.0"  # Version of inference model (for cache invalidation)
    SYSTEM_SOURCE_ID: str | None = None  # UUID of system source (created on startup)

    # Flags
    STRICT_VALIDATION: bool = True
    SQL_DEBUG: bool = False

    model_config = ConfigDict(
        env_file=".env.test",  # Test configuration (not tracked by git)
        env_file_encoding="utf-8",
        case_sensitive=True
    )


settings = Settings()