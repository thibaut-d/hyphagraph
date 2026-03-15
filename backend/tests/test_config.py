import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_require_secret_key_when_no_env_file():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            _env_file=None,
            DATABASE_URL="sqlite+aiosqlite:///./test.db",
        )


def test_admin_bootstrap_credentials_are_optional():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        SECRET_KEY="test-secret",
    )

    assert settings.ADMIN_EMAIL is None
    assert settings.ADMIN_PASSWORD is None
