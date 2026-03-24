from pydantic_settings import BaseSettings
from pydantic import ConfigDict, model_validator


class Settings(BaseSettings):
    # Global
    ENV: str = "development"
    PROJECT_NAME: str = "hyphagraph"
    LOG_LEVEL: str = "info"

    # Database
    DATABASE_URL: str

    # Security / Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"  # JWT signing algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # JWT token expiration (30 minutes)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh token expiration (7 days)
    BCRYPT_ROUNDS: int = 12  # Bcrypt cost factor (10=fast for dev/test, 12=secure for prod)

    # Admin bootstrap credentials (used only by explicit bootstrap/setup flows)
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None

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

    # LLM Configuration
    OPENAI_API_KEY: str | None = None  # OpenAI API key for ChatGPT
    OPENAI_MODEL: str = "gpt-4o-mini"  # OpenAI model to use (gpt-4o-mini, gpt-4o, gpt-4-turbo)
    LLM_PROVIDER: str = "openai"  # LLM provider identifier stored in provenance (e.g., "openai", "anthropic")
    OPENAI_TEMPERATURE: float = 0.3  # Temperature for LLM responses (0.0-1.0, lower = more deterministic)

    # Cookie settings (for httpOnly refresh token)
    COOKIE_SECURE: bool = False  # Set True in production (requires HTTPS)
    COOKIE_SAMESITE: str = "lax"  # "lax" works for same-site; use "none" only with HTTPS cross-site
    COOKIE_DOMAIN: str | None = None  # None = current domain

    # CORS (must be specific origins, not "*", when credentials/cookies are used)
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Flags
    STRICT_VALIDATION: bool = True
    SQL_DEBUG: bool = False
    TESTING: bool = False  # Enable test-only endpoints (e.g., /api/test/reset-database)

    @model_validator(mode="after")
    def _block_placeholder_secrets_in_production(self) -> "Settings":
        if self.ENV != "production":
            return self
        checks = {
            "SECRET_KEY": self.SECRET_KEY,
            "DATABASE_URL": self.DATABASE_URL,
        }
        if self.ADMIN_PASSWORD:
            checks["ADMIN_PASSWORD"] = self.ADMIN_PASSWORD
        _placeholder_patterns = ("change-me", "changeme", "placeholder", "your-secret", "your_secret", "insert-secret")
        bad = [name for name, val in checks.items() if any(p in val.lower() for p in _placeholder_patterns)]
        if bad:
            raise ValueError(
                f"Production startup blocked — these variables still contain placeholder values: "
                f"{', '.join(bad)}. "
                f"Run 'bash scripts/setup-self-host.sh' or edit your .env file."
            )
        return self

    model_config = ConfigDict(
        env_file=".env",  # Development configuration (not tracked by git) - overridden by environment variables
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables
    )


settings = Settings()
