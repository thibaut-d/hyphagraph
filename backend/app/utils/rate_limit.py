"""
Rate limiting utilities for FastAPI endpoints.

Uses slowapi for request rate limiting to prevent abuse.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


class ToggleableLimiter(Limiter):
    """
    Small slowapi wrapper that keeps the enabled flag overrideable in tests.

    Existing unit tests toggle `limiter._enabled`; surfacing `enabled` through the
    same backing attribute keeps those direct endpoint tests working while runtime
    behavior remains unchanged.
    """

    @property
    def enabled(self):
        return getattr(self, "_enabled", True)

    @enabled.setter
    def enabled(self, value):
        self._enabled = value


def rate_limit_key(request):
    """
    Generate rate limit key based on client IP address.

    For authenticated requests, you could also use user_id,
    but IP-based limiting is simpler and prevents enumeration attacks.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address for rate limiting
    """
    return get_remote_address(request)


# Global limiter instance
limiter = ToggleableLimiter(
    key_func=rate_limit_key,
    enabled=settings.RATE_LIMIT_ENABLED,
    storage_uri="memory://",  # In-memory storage (use Redis in production for multi-process)
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)
