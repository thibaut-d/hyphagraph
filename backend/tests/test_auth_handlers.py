from fastapi import Response

from app.api.auth_handlers import _clear_refresh_cookie
from app.config import settings


def test_clear_refresh_cookie_uses_cookie_domain(monkeypatch):
    response = Response()
    monkeypatch.setattr(settings, "COOKIE_DOMAIN", ".example.com")

    _clear_refresh_cookie(response)

    cookie_header = response.headers.get("set-cookie", "")
    assert "refresh_token=" in cookie_header
    assert "Domain=.example.com" in cookie_header
    assert "Path=/api/auth" in cookie_header
