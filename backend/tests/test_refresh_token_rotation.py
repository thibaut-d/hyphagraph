"""
Refresh token rotation with a short reuse grace period.

The access token lives in memory only, so every page load / new tab calls
/auth/refresh. Concurrent tabs, or a reload that aborts an in-flight refresh,
can present a token the server has just rotated. Within the grace window that
token is still accepted — unless its successor was revoked (logout, password
change), which must keep cutting access immediately.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.user.tokens import purge_expired_tokens
from app.services.user_service import UserService
from app.utils.auth import hash_token_for_lookup
from app.utils.errors import UnauthorizedException


async def _setup(db_session):
    user = User(
        id=uuid4(),
        email=f"rotation-{uuid4()}@example.com",
        hashed_password="x",
        is_active=True,
        is_verified=True,
        token_version=0,
    )
    db_session.add(user)
    await db_session.flush()
    service = UserService(db_session)
    _, token = await service.create_refresh_token(user)
    return service, token


async def _row(db_session, token: str) -> RefreshToken:
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.token_lookup_hash == hash_token_for_lookup(token))
    )
    return result.scalar_one()


async def _age_revocation(db_session, token: str, seconds: int) -> None:
    row = await _row(db_session, token)
    await db_session.execute(
        update(RefreshToken)
        .where(RefreshToken.id == row.id)
        .values(revoked_at=datetime.now(timezone.utc) - timedelta(seconds=seconds))
    )
    await db_session.commit()
    db_session.expire_all()


@pytest.mark.asyncio
async def test_rotation_revokes_and_links_successor(db_session):
    service, t0 = await _setup(db_session)
    _, t1, _ = await service.refresh_access_token_with_user(t0)

    old, new = await _row(db_session, t0), await _row(db_session, t1)
    assert old.is_revoked and old.revoked_at is not None
    assert old.replaced_by_id == new.id
    assert not new.is_revoked


@pytest.mark.asyncio
async def test_just_rotated_token_accepted_within_grace(db_session):
    """Second tab / aborted reload presenting the pre-rotation token keeps the session."""
    service, t0 = await _setup(db_session)
    _, t1, _ = await service.refresh_access_token_with_user(t0)

    _, t2, _ = await service.refresh_access_token_with_user(t0)

    # Both successors remain usable: whichever cookie the browser kept works.
    assert not (await _row(db_session, t1)).is_revoked
    assert not (await _row(db_session, t2)).is_revoked


@pytest.mark.asyncio
async def test_rotated_token_rejected_after_grace(db_session):
    service, t0 = await _setup(db_session)
    await service.refresh_access_token_with_user(t0)
    await _age_revocation(db_session, t0, seconds=3600)

    with pytest.raises(UnauthorizedException):
        await service.refresh_access_token_with_user(t0)


@pytest.mark.asyncio
async def test_rotated_token_rejected_after_logout(db_session):
    """Logout revokes the active successor; the old token must not resurrect the session."""
    service, t0 = await _setup(db_session)
    _, t1, _ = await service.refresh_access_token_with_user(t0)
    user_id = (await _row(db_session, t1)).user_id
    await service.revoke_refresh_token(user_id, t1)

    with pytest.raises(UnauthorizedException):
        await service.refresh_access_token_with_user(t0)


@pytest.mark.asyncio
async def test_grace_follows_rotation_chain(db_session):
    """t0 -> t1 -> t2 in quick succession: t0 is still accepted while t2 is active."""
    service, t0 = await _setup(db_session)
    _, t1, _ = await service.refresh_access_token_with_user(t0)
    await service.refresh_access_token_with_user(t1)

    await service.refresh_access_token_with_user(t0)


@pytest.mark.asyncio
async def test_never_issued_token_rejected(db_session):
    service, _ = await _setup(db_session)
    with pytest.raises(UnauthorizedException):
        await service.refresh_access_token_with_user("not-a-real-token")


@pytest.mark.asyncio
async def test_purge_keeps_tokens_inside_grace_window(db_session):
    service, t0 = await _setup(db_session)
    await service.refresh_access_token_with_user(t0)

    await purge_expired_tokens(db_session)
    db_session.expire_all()
    assert (await _row(db_session, t0)).is_revoked  # still present

    await _age_revocation(db_session, t0, seconds=3600)
    await purge_expired_tokens(db_session)
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.token_lookup_hash == hash_token_for_lookup(t0))
    )
    assert result.scalar_one_or_none() is None
