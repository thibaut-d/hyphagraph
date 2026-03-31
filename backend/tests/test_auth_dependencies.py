from unittest.mock import AsyncMock, patch

import pytest

from app.dependencies.auth import get_optional_current_user
from app.utils.errors import ForbiddenException, UnauthorizedException


class TestGetOptionalCurrentUser:
    @pytest.mark.asyncio
    async def test_returns_none_when_token_missing(self):
        db = AsyncMock()

        result = await get_optional_current_user(token=None, db=db)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_unauthorized_token(self):
        db = AsyncMock()

        with patch("app.dependencies.auth.get_current_user", new=AsyncMock()) as mock_get_current_user:
            mock_get_current_user.side_effect = UnauthorizedException(
                message="Could not validate credentials",
                details="Invalid or expired token",
            )

            result = await get_optional_current_user(token="bad-token", db=db)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_forbidden_user(self):
        db = AsyncMock()

        with patch("app.dependencies.auth.get_current_user", new=AsyncMock()) as mock_get_current_user:
            mock_get_current_user.side_effect = ForbiddenException(
                message="Inactive user",
                details="Your account has been deactivated",
            )

            result = await get_optional_current_user(token="inactive-user-token", db=db)

        assert result is None

    @pytest.mark.asyncio
    async def test_reraises_unexpected_failures(self):
        db = AsyncMock()

        with patch("app.dependencies.auth.get_current_user", new=AsyncMock()) as mock_get_current_user:
            mock_get_current_user.side_effect = RuntimeError("database unavailable")

            with pytest.raises(RuntimeError, match="database unavailable"):
                await get_optional_current_user(token="valid-looking-token", db=db)
