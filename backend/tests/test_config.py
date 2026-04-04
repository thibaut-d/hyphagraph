import pytest
from pydantic import ValidationError

from app.config import Settings

# Env vars set by the container that would interfere with isolation tests.
_ISOLATION_VARS = [
    "SECRET_KEY", "DATABASE_URL", "ADMIN_EMAIL", "ADMIN_PASSWORD",
    "JWT_SECRET_KEY",
]


def test_settings_require_secret_key_when_no_env_file(monkeypatch):
    for var in _ISOLATION_VARS:
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            _env_file=None,
            DATABASE_URL="sqlite+aiosqlite:///./test.db",
        )


def test_admin_bootstrap_credentials_are_optional(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    settings = Settings(
        _env_file=None,
        DATABASE_URL="sqlite+aiosqlite:///./test.db",
        SECRET_KEY="test-secret",
    )
    assert settings.ADMIN_EMAIL is None
    assert settings.ADMIN_PASSWORD is None
