from unittest.mock import AsyncMock, patch

import pytest

from app.startup import bootstrap_admin_user, run_bootstrap_tasks, run_startup_tasks


@pytest.mark.asyncio
async def test_run_startup_tasks_skips_admin_bootstrap(db_session):
    with patch("app.startup.bootstrap_admin_user", new_callable=AsyncMock) as mock_bootstrap:
        await run_startup_tasks(db_session)

    mock_bootstrap.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_bootstrap_tasks_bootstraps_admin_and_system_source(db_session):
    with patch("app.startup.create_system_source", new_callable=AsyncMock) as mock_system_source, \
         patch("app.startup.bootstrap_admin_user", new_callable=AsyncMock) as mock_bootstrap:
        await run_bootstrap_tasks(db_session)

    mock_system_source.assert_awaited_once_with(db_session)
    mock_bootstrap.assert_awaited_once_with(db_session)


@pytest.mark.asyncio
async def test_bootstrap_admin_user_requires_configured_credentials(db_session, monkeypatch):
    monkeypatch.setattr("app.startup.settings.ADMIN_EMAIL", None)
    monkeypatch.setattr("app.startup.settings.ADMIN_PASSWORD", None)

    with pytest.raises(RuntimeError, match="ADMIN_EMAIL and ADMIN_PASSWORD"):
        await bootstrap_admin_user(db_session)
