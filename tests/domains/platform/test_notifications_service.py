"""
Unit tests for Notifications Service (Domain Layer).

Tests v3.32 enhancements:
1. Repository dependency injection
2. @audit_log decorator integration

@module tests.domains.platform.test_notifications_service
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from domains.platform.notifications.service import (
    send_broadcast,
    send_to_user,
    send_to_users,
    get_stats,
    get_history,
)


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_notification_repo():
    """Create mock NotificationRepository."""
    repo = AsyncMock()
    # Add all required methods
    repo.create_notification = AsyncMock(return_value={"id": "notif-1"})
    repo.send_notification_to_user = AsyncMock(return_value={"id": "notif-1"})
    repo.send_notification_to_users = AsyncMock(return_value=[{"id": "notif-1"}])
    repo.get_all_notification_stats = AsyncMock(return_value={"total": 0})
    repo.get_notification_history = AsyncMock(return_value={"items": [], "total": 0})
    return repo


@pytest.fixture
def mock_db_client():
    """Create mock database client (async compatible)."""
    client = MagicMock()
    # Mock profiles table query result
    profiles_result = MagicMock()
    profiles_result.data = [{"id": "user-1"}, {"id": "user-2"}]

    # Fix: Make execute() async-compatible
    execute_mock = AsyncMock(return_value=profiles_result)

    client.table.return_value.select.return_value.execute = execute_mock
    client.table.return_value.select.return_value.eq.return_value.execute = execute_mock
    return client


# ==========================================
# Repository Dependency Injection Tests
# ==========================================

class TestRepositoryDependencyInjection:
    """Tests for Repository dependency injection functionality."""

    @pytest.mark.asyncio
    async def test_send_broadcast_with_injected_repo(self, mock_notification_repo, mock_db_client):
        """send_broadcast accepts injected Repository."""
        # Arrange
        mock_notification_repo.create_notification.return_value = {"id": "notif-1"}

        # Fix: Use get_async_db_client (not get_database_client) and make it AsyncMock
        with patch("core.database.get_async_db_client", new_callable=AsyncMock) as mock_get_db:
            mock_get_db.return_value = mock_db_client

            # Act
            result = await send_broadcast(
                title="Test Broadcast",
                content="Test content",
                target_group="all",
                admin_id="admin-123",
                notification_repo=mock_notification_repo,  # ← Injected
            )

        # Assert
        assert result["title"] == "Test Broadcast"
        assert result["target_group"] == "all"
        assert result["user_count"] == 2
        assert result["notification_count"] == 2
        assert mock_notification_repo.create_notification.call_count == 2

    @pytest.mark.asyncio
    async def test_send_to_user_with_injected_repo(self, mock_notification_repo):
        """send_to_user accepts injected Repository."""
        # Arrange
        mock_notification_repo.send_notification_to_user.return_value = {
            "id": "notif-1",
            "title": "Test",
        }

        # Act
        result = await send_to_user(
            user_id="user-123",
            title="Test",
            content="Test content",
            notification_type="system",
            admin_id="admin-123",
            notification_repo=mock_notification_repo,  # ← Injected
        )

        # Assert
        assert result["status"] == "sent"
        assert result["notification"]["id"] == "notif-1"
        mock_notification_repo.send_notification_to_user.assert_called_once_with(
            user_id="user-123",
            title="Test",
            content="Test content",
            notification_type="system",
        )

    @pytest.mark.asyncio
    async def test_send_to_users_with_injected_repo(self, mock_notification_repo):
        """send_to_users accepts injected Repository."""
        # Arrange
        mock_notification_repo.send_notification_to_users.return_value = [
            {"id": "notif-1"},
            {"id": "notif-2"},
        ]

        # Act
        result = await send_to_users(
            user_ids=["user-1", "user-2"],
            title="Test",
            content="Test content",
            notification_type="alert",
            admin_id="admin-123",
            notification_repo=mock_notification_repo,  # ← Injected
        )

        # Assert
        assert result["status"] == "sent"
        assert result["count"] == 2
        mock_notification_repo.send_notification_to_users.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats_with_injected_repo(self, mock_notification_repo):
        """get_stats accepts injected Repository."""
        # Arrange
        mock_notification_repo.get_all_notification_stats.return_value = {
            "total": 100,
            "unread": 20,
        }

        # Act
        result = await get_stats(notification_repo=mock_notification_repo)

        # Assert
        assert result["total"] == 100
        assert result["unread"] == 20
        mock_notification_repo.get_all_notification_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_with_injected_repo(self, mock_notification_repo):
        """get_history accepts injected Repository."""
        # Arrange
        mock_notification_repo.get_notification_history.return_value = {
            "items": [{"id": "notif-1"}],
            "total": 1,
        }

        # Act
        result = await get_history(
            offset=0,
            limit=50,
            notification_repo=mock_notification_repo,
        )

        # Assert
        assert result["total"] == 1
        assert len(result["items"]) == 1
        mock_notification_repo.get_notification_history.assert_called_once_with(
            offset=0, limit=50
        )


# ==========================================
# Audit Log Decorator Tests
# ==========================================

class TestAuditLogDecorator:
    """Tests for @audit_log decorator integration."""

    @pytest.mark.asyncio
    async def test_send_broadcast_creates_audit_logs(self, mock_notification_repo):
        """send_broadcast creates audit logs via decorator."""
        # Arrange
        # Fix: Create async-compatible mock db client
        mock_db = MagicMock()
        profiles_result = MagicMock()
        profiles_result.data = [{"id": "user-1"}]
        execute_mock = AsyncMock(return_value=profiles_result)
        mock_db.table.return_value.select.return_value.execute = execute_mock

        mock_notification_repo.create_notification.return_value = {"id": "notif-1"}

        # Fix: Use get_async_db_client and make it AsyncMock
        with patch("core.database.get_async_db_client", new_callable=AsyncMock) as mock_get_db:
            mock_get_db.return_value = mock_db

            # Mock audit repositories
            with patch("infrastructure.repositories.SupabaseAdminStatsRepository") as MockStatsRepo:
                with patch("infrastructure.repositories.SupabaseAdminUsersRepository") as MockAdminRepo:
                        mock_stats_instance = AsyncMock()
                        mock_admin_instance = AsyncMock()
                        MockStatsRepo.return_value = mock_stats_instance
                        MockAdminRepo.return_value = mock_admin_instance

                        # Act
                        result = await send_broadcast(
                            title="Test",
                            content="Content",
                            target_group="all",
                            admin_id="admin-123",
                            notification_repo=mock_notification_repo,
                        )

                        # Assert - Audit logging was called
                        mock_stats_instance.log_user_event.assert_called_once()
                        mock_admin_instance.admin_log_operation.assert_called_once()

                        # Check audit log arguments
                        stats_call = mock_stats_instance.log_user_event.call_args
                        assert stats_call[0][0] == "admin-123"  # admin_id
                        assert stats_call[0][1] == "admin_broadcast"  # event_type

                        admin_call = mock_admin_instance.admin_log_operation.call_args
                        assert admin_call[1]["admin_id"] == "admin-123"
                        assert admin_call[1]["operation_type"] == "broadcast"

    @pytest.mark.asyncio
    async def test_send_to_user_creates_audit_logs_with_target(
        self, mock_notification_repo
    ):
        """send_to_user creates audit logs with target_user_id."""
        # Arrange
        mock_notification_repo.send_notification_to_user.return_value = {"id": "notif-1"}

        # Fix: Use get_async_db_client with AsyncMock
        with patch("core.database.get_async_db_client", new_callable=AsyncMock) as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # Mock audit repositories
            with patch("infrastructure.repositories.SupabaseAdminStatsRepository") as MockStatsRepo:
                with patch("infrastructure.repositories.SupabaseAdminUsersRepository") as MockAdminRepo:
                        mock_stats_instance = AsyncMock()
                        mock_admin_instance = AsyncMock()
                        MockStatsRepo.return_value = mock_stats_instance
                        MockAdminRepo.return_value = mock_admin_instance

                        # Act
                        result = await send_to_user(
                            user_id="user-456",
                            title="Test",
                            content="Content",
                            notification_type="system",
                            admin_id="admin-123",
                            notification_repo=mock_notification_repo,
                        )

                        # Assert - target_user_id was set
                        admin_call = mock_admin_instance.admin_log_operation.call_args
                        assert admin_call[1]["target_user_id"] == "user-456"

    @pytest.mark.asyncio
    async def test_audit_log_failure_does_not_break_operation(
        self, mock_notification_repo
    ):
        """Audit log failure does not prevent operation success."""
        # Arrange
        # Fix: Create async-compatible mock db client
        mock_db = MagicMock()
        profiles_result = MagicMock()
        profiles_result.data = [{"id": "user-1"}]
        execute_mock = AsyncMock(return_value=profiles_result)
        mock_db.table.return_value.select.return_value.execute = execute_mock

        mock_notification_repo.create_notification.return_value = {"id": "notif-1"}

        # Fix: Use get_async_db_client with AsyncMock
        with patch("core.database.get_async_db_client", new_callable=AsyncMock) as mock_get_db:
            mock_get_db.return_value = mock_db

            # Mock audit repositories to raise exception
            with patch("infrastructure.repositories.SupabaseAdminStatsRepository") as MockStatsRepo:
                MockStatsRepo.side_effect = Exception("Audit log failed")

                # Act - Should not raise exception
                result = await send_broadcast(
                    title="Test",
                    content="Content",
                    target_group="all",
                    admin_id="admin-123",
                    notification_repo=mock_notification_repo,
                )

                # Assert - Operation succeeded despite audit failure
                assert result["notification_count"] == 1


# ==========================================
# Integration Tests (Factory Functions)
# ==========================================

class TestFactoryFunctions:
    """Tests for Repository factory functions."""

    @pytest.mark.asyncio
    async def test_send_broadcast_uses_default_repo_when_none_provided(self, mock_db_client):
        """send_broadcast uses default Repository when none provided."""
        # Fix: Use get_async_db_client with AsyncMock
        with patch("core.database.get_async_db_client", new_callable=AsyncMock) as mock_get_db:
            mock_get_db.return_value = mock_db_client

            with patch(
                "infrastructure.repositories.SupabaseNotificationRepository"
            ) as MockRepo:
                mock_repo_instance = AsyncMock()
                mock_repo_instance.create_notification.return_value = {"id": "notif-1"}
                MockRepo.return_value = mock_repo_instance

                # Act - No notification_repo parameter
                result = await send_broadcast(
                    title="Test",
                    content="Content",
                    target_group="all",
                    admin_id="admin-123",
                )

                # Assert - Factory created default repository
                MockRepo.assert_called_once_with(mock_db_client)
                assert result["notification_count"] == 2

    @pytest.mark.asyncio
    async def test_send_to_user_uses_injected_repo_over_default(self, mock_notification_repo):
        """send_to_user uses injected Repository instead of default."""
        mock_notification_repo.send_notification_to_user.return_value = {"id": "notif-1"}

        with patch(
            "infrastructure.repositories.SupabaseNotificationRepository"
        ) as MockRepo:
            # Act - Provide notification_repo
            result = await send_to_user(
                user_id="user-123",
                title="Test",
                content="Content",
                notification_type="system",
                admin_id="admin-123",
                notification_repo=mock_notification_repo,
            )

            # Assert - Default repository was NOT created
            MockRepo.assert_not_called()
            # Injected repository was used
            mock_notification_repo.send_notification_to_user.assert_called_once()
