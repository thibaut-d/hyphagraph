from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Global
    ENV: str = "development"
    PROJECT_NAME: str = "hyphagraph"
    LOG_LEVEL: str = "info"

    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Flags
    STRICT_VALIDATION: bool = True
    SQL_DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()