"""
Tests for purge_expired_tokens().

Verifies that expired and revoked refresh token rows are deleted while
active (non-expired, non-revoked) rows are preserved.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.user.tokens import purge_expired_tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _create_user(db) -> User:
    user = User(
        id=uuid4(),
        email=f"purge-test-{uuid4()}@example.com",
        hashed_password="x",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


def _make_token(user_id, *, expires_at, is_revoked=False):
    return RefreshToken(
        id=uuid4(),
        user_id=user_id,
        token_lookup_hash=uuid4().hex,
        token_hash="hash",
        expires_at=expires_at,
        is_revoked=is_revoked,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_purge_deletes_expired_tokens(db_session):
    """Tokens past their expiry date are removed."""
    user = await _create_user(db_session)
    expired = _make_token(user.id, expires_at=_now() - timedelta(days=1))
    db_session.add(expired)
    await db_session.flush()

    deleted = await purge_expired_tokens(db_session)

    assert deleted >= 1
    remaining = (await db_session.execute(
        select(RefreshToken).where(RefreshToken.id == expired.id)
    )).scalar_one_or_none()
    assert remaining is None


@pytest.mark.asyncio
async def test_purge_deletes_revoked_tokens(db_session):
    """Revoked tokens (not yet expired) are removed."""
    user = await _create_user(db_session)
    revoked = _make_token(
        user.id,
        expires_at=_now() + timedelta(days=7),
        is_revoked=True,
    )
    db_session.add(revoked)
    await db_session.flush()

    deleted = await purge_expired_tokens(db_session)

    assert deleted >= 1
    remaining = (await db_session.execute(
        select(RefreshToken).where(RefreshToken.id == revoked.id)
    )).scalar_one_or_none()
    assert remaining is None


@pytest.mark.asyncio
async def test_purge_keeps_active_tokens(db_session):
    """Active (non-expired, non-revoked) tokens are not touched."""
    user = await _create_user(db_session)
    active = _make_token(user.id, expires_at=_now() + timedelta(days=7))
    db_session.add(active)
    await db_session.flush()

    await purge_expired_tokens(db_session)

    remaining = (await db_session.execute(
        select(RefreshToken).where(RefreshToken.id == active.id)
    )).scalar_one_or_none()
    assert remaining is not None


@pytest.mark.asyncio
async def test_purge_returns_correct_count(db_session):
    """Return value reflects exact number of rows deleted."""
    user = await _create_user(db_session)
    tokens = [
        _make_token(user.id, expires_at=_now() - timedelta(hours=1)),   # expired
        _make_token(user.id, expires_at=_now() + timedelta(days=7), is_revoked=True),  # revoked
        _make_token(user.id, expires_at=_now() + timedelta(days=7)),     # active
    ]
    for t in tokens:
        db_session.add(t)
    await db_session.flush()

    deleted = await purge_expired_tokens(db_session)

    assert deleted == 2


@pytest.mark.asyncio
async def test_purge_noop_when_nothing_to_delete(db_session):
    """Returns 0 when there are no expired or revoked tokens."""
    user = await _create_user(db_session)
    active = _make_token(user.id, expires_at=_now() + timedelta(days=7))
    db_session.add(active)
    await db_session.flush()

    deleted = await purge_expired_tokens(db_session)

    assert deleted == 0
