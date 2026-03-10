"""
Tests for test helper endpoints.

These tests verify the /api/test/* endpoint logic works correctly.
Note: The endpoints are only registered when TESTING=True at app startup,
so we test the endpoint functions directly rather than via HTTP client.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import text
from fastapi import HTTPException

from app.api.test_helpers import check_testing_mode, reset_database, test_health
from app.config import settings


class TestTestHelpers:
    """Test the test helper endpoint logic."""

    def test_check_testing_mode_raises_when_disabled(self):
        """Test that check_testing_mode dependency raises 403 when TESTING=False."""
        # Arrange - ensure TESTING is False by default in tests
        original_testing = settings.TESTING
        settings.TESTING = False

        try:
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                check_testing_mode()

            assert exc_info.value.status_code == 403
            assert "only available when TESTING=True" in exc_info.value.detail
        finally:
            settings.TESTING = original_testing

    def test_check_testing_mode_succeeds_when_enabled(self):
        """Test that check_testing_mode dependency succeeds when TESTING=True."""
        # Arrange
        original_testing = settings.TESTING
        settings.TESTING = True

        try:
            # Act & Assert - should not raise
            check_testing_mode()
        finally:
            settings.TESTING = original_testing

    @pytest.mark.asyncio
    async def test_reset_database_truncates_tables(self):
        """Test that reset_database correctly truncates all tables."""
        # Arrange - mock database session
        mock_db = AsyncMock()

        # Mock the table query result
        mock_table_result = MagicMock()
        mock_table_result.fetchall.return_value = [
            ("entities",),
            ("sources",),
            ("relations",),
        ]

        # Track SQL commands executed
        executed_commands = []

        async def track_execute(sql):
            executed_commands.append(str(sql))
            if "SELECT tablename" in str(sql):
                return mock_table_result
            return MagicMock()

        mock_db.execute = track_execute
        mock_db.commit = AsyncMock()

        # Act
        result = await reset_database(db=mock_db)

        # Assert
        assert result["tables_truncated"] == 3
        assert "entities" in result["tables"]
        assert "sources" in result["tables"]
        assert "relations" in result["tables"]

        # Verify correct SQL sequence
        sql_commands = " ".join(executed_commands)
        assert "SELECT tablename" in sql_commands
        assert "SET session_replication_role = 'replica'" in sql_commands
        assert "TRUNCATE TABLE entities" in sql_commands
        assert "TRUNCATE TABLE sources" in sql_commands
        assert "TRUNCATE TABLE relations" in sql_commands
        assert "SET session_replication_role = 'origin'" in sql_commands

    @pytest.mark.asyncio
    async def test_reset_database_handles_empty_database(self):
        """Test that reset_database handles case with no tables gracefully."""
        # Arrange
        mock_db = AsyncMock()
        mock_table_result = MagicMock()
        mock_table_result.fetchall.return_value = []

        async def mock_execute(sql):
            if "SELECT tablename" in str(sql):
                return mock_table_result
            return MagicMock()

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()

        # Act
        result = await reset_database(db=mock_db)

        # Assert
        assert result["tables_truncated"] == 0
        assert "No tables to truncate" in result["message"]

    @pytest.mark.asyncio
    async def test_reset_database_rollback_on_error(self):
        """Test that reset_database rolls back on error."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("DB error"))
        mock_db.rollback = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await reset_database(db=mock_db)

        assert exc_info.value.status_code == 500
        assert "Failed to reset database" in exc_info.value.detail
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_endpoint_returns_correct_status(self):
        """Test that test health endpoint returns correct status."""
        # Arrange
        original_testing = settings.TESTING
        settings.TESTING = True

        try:
            # Act
            result = await test_health()

            # Assert
            assert result["status"] == "ok"
            assert result["testing_mode"] is True
            assert "Test helper endpoints are available" in result["message"]
        finally:
            settings.TESTING = original_testing
