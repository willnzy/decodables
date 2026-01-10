"""
Tests for BaseRepository - Unified delete mechanism.

@module tests.infrastructure.repositories.test_base_repository
@version 1.0.0

Tests the abstract BaseRepository class soft/hard delete operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from infrastructure.repositories.base_repository import BaseRepository


# ==========================================
# Concrete Test Repository
# ==========================================

class TestEntity:
    """Test entity for repository."""
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


class ConcreteTestRepository(BaseRepository[TestEntity]):
    """
    Concrete implementation of BaseRepository for testing.

    Uses a simple TestEntity with id and name fields.
    """

    @property
    def table_name(self) -> str:
        return "test_table"

    def _map_to_entity(self, row: Dict[str, Any]) -> TestEntity:
        return TestEntity(id=row["id"], name=row["name"])

    def _map_to_row(self, entity: TestEntity) -> Dict[str, Any]:
        return {"id": entity.id, "name": entity.name}


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_db_client():
    """Create mock Supabase client."""
    client = MagicMock()
    return client


@pytest.fixture
def test_repo(mock_db_client):
    """Create ConcreteTestRepository instance."""
    return ConcreteTestRepository(mock_db_client)


# ==========================================
# Soft Delete Tests
# ==========================================

@pytest.mark.asyncio
class TestSoftDelete:
    """Tests for soft_delete method."""

    async def test_soft_delete_success(self, test_repo, mock_db_client):
        """Successfully soft delete a record."""
        # Mock recovery period config
        test_repo._get_recovery_period_days = AsyncMock(return_value=30)

        # Mock successful deletion
        mock_result = MagicMock()
        mock_result.data = [{"id": "123", "is_deleted": True}]

        # Setup mock chain
        mock_db_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        # Execute
        result = await test_repo.soft_delete("123")

        # Assert
        assert result is True

        # Verify call chain
        mock_db_client.table.assert_called_once_with("test_table")
        update_call = mock_db_client.table.return_value.update.call_args[0][0]
        assert update_call["is_deleted"] is True
        assert "deleted_at" in update_call
        assert "recovery_expires_at" in update_call  # New field

    async def test_soft_delete_with_user_id(self, test_repo, mock_db_client):
        """Soft delete with user ownership check."""
        # Mock recovery period config
        test_repo._get_recovery_period_days = AsyncMock(return_value=30)

        mock_result = MagicMock()
        mock_result.data = [{"id": "123"}]

        mock_db_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        result = await test_repo.soft_delete("123", user_id="user_456")

        assert result is True
        # Verify both id and user_id were used as filters
        # The implementation chains .eq("id", ...).eq("user_id", ...)
        mock_db_client.table.return_value.update.return_value.eq.assert_called()
        mock_db_client.table.return_value.update.return_value.eq.return_value.eq.assert_called_with("user_id", "user_456")

    async def test_soft_delete_not_found(self, test_repo, mock_db_client):
        """Soft delete fails when record not found."""
        # Mock recovery period config
        test_repo._get_recovery_period_days = AsyncMock(return_value=30)

        mock_result = MagicMock()
        mock_result.data = None

        mock_db_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        result = await test_repo.soft_delete("nonexistent")

        assert result is False

    async def test_soft_delete_exception(self, test_repo, mock_db_client):
        """Soft delete raises exception on database error."""
        # Mock recovery period config
        test_repo._get_recovery_period_days = AsyncMock(return_value=30)

        mock_db_client.table.return_value.update.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await test_repo.soft_delete("123")


# ==========================================
# Restore Tests
# ==========================================

@pytest.mark.asyncio
class TestRestore:
    """Tests for restore method."""

    async def test_restore_success(self, test_repo, mock_db_client):
        """Successfully restore a soft-deleted record."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "123", "is_deleted": False}]

        mock_db_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        result = await test_repo.restore("123")

        assert result is True

        # Verify update data
        update_call = mock_db_client.table.return_value.update.call_args[0][0]
        assert update_call["is_deleted"] is False
        assert update_call["deleted_at"] is None

    async def test_restore_not_deleted(self, test_repo, mock_db_client):
        """Restore fails when record is not soft-deleted."""
        mock_result = MagicMock()
        mock_result.data = None  # No records match (not soft-deleted)

        mock_db_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        result = await test_repo.restore("123")

        assert result is False


# ==========================================
# Hard Delete Tests
# ==========================================

@pytest.mark.asyncio
class TestHardDelete:
    """Tests for hard_delete method."""

    async def test_hard_delete_stage2_with_permanent_flag(self, test_repo, mock_db_client):
        """Hard delete Stage 2 (is_permanently_deleted = true)."""
        # Mock _supports_permanent_delete_flag to return True
        test_repo._supports_permanent_delete_flag = AsyncMock(return_value=True)

        mock_result = MagicMock()
        mock_result.data = [{"id": "123", "is_permanently_deleted": True}]

        mock_db_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        result = await test_repo.hard_delete("123", permanent_delete=False)

        assert result is True

        # Verify it uses UPDATE, not DELETE
        update_call = mock_db_client.table.return_value.update.call_args[0][0]
        assert update_call["is_permanently_deleted"] is True

    async def test_hard_delete_physical_deletion(self, test_repo, mock_db_client):
        """Hard delete with physical deletion (DELETE FROM table)."""
        # Mock _supports_permanent_delete_flag to return True
        test_repo._supports_permanent_delete_flag = AsyncMock(return_value=True)

        mock_result = MagicMock()
        mock_result.data = [{"id": "123"}]

        mock_db_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result

        result = await test_repo.hard_delete("123", permanent_delete=True)

        assert result is True

        # Verify it uses DELETE
        mock_db_client.table.return_value.delete.assert_called_once()

    async def test_hard_delete_no_permanent_flag_support(self, test_repo, mock_db_client):
        """Hard delete when table doesn't support is_permanently_deleted."""
        # Mock _supports_permanent_delete_flag to return False
        test_repo._supports_permanent_delete_flag = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.data = [{"id": "123"}]

        mock_db_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_result

        result = await test_repo.hard_delete("123")

        assert result is True
        # Should use physical deletion when no permanent flag support
        mock_db_client.table.return_value.delete.assert_called_once()


# ==========================================
# Query Helper Tests
# ==========================================

@pytest.mark.asyncio
class TestQueryHelpers:
    """Tests for query helper methods."""

    async def test_query_active_only(self, test_repo, mock_db_client):
        """Query active records (is_deleted = false)."""
        query = test_repo._query_active_only()

        # Verify it filters by is_deleted = false
        mock_db_client.table.assert_called_with("test_table")
        mock_db_client.table.return_value.select.assert_called_with("*")
        mock_db_client.table.return_value.select.return_value.eq.assert_called_with("is_deleted", False)

    async def test_query_active_only_custom_select(self, test_repo, mock_db_client):
        """Query active records with custom select fields."""
        query = test_repo._query_active_only("id, name")

        mock_db_client.table.return_value.select.assert_called_with("id, name")

    async def test_query_deleted_only(self, test_repo, mock_db_client):
        """Query soft-deleted records (is_deleted = true)."""
        query = test_repo._query_deleted_only()

        mock_db_client.table.return_value.select.return_value.eq.assert_called_with("is_deleted", True)

    async def test_query_all(self, test_repo, mock_db_client):
        """Query all records (no delete filter)."""
        query = test_repo._query_all()

        # Should only call table().select(), no eq() for is_deleted
        mock_db_client.table.assert_called_with("test_table")
        mock_db_client.table.return_value.select.assert_called_with("*")


# ==========================================
# Common CRUD Tests
# ==========================================

@pytest.mark.asyncio
class TestCommonCRUD:
    """Tests for common CRUD operations."""

    async def test_get_by_id_active_only(self, test_repo, mock_db_client):
        """Get record by ID (excluding deleted)."""
        mock_result = MagicMock()
        mock_result.data = {"id": "123", "name": "Test"}

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

        result = await test_repo.get_by_id("123")

        assert result is not None
        assert result.id == "123"
        assert result.name == "Test"

    async def test_get_by_id_include_deleted(self, test_repo, mock_db_client):
        """Get record by ID including deleted."""
        mock_result = MagicMock()
        mock_result.data = {"id": "123", "name": "Deleted Record", "is_deleted": True}

        mock_db_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

        result = await test_repo.get_by_id("123", include_deleted=True)

        assert result is not None
        assert result.id == "123"

    async def test_exists_active_record(self, test_repo, mock_db_client):
        """Check if active record exists."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "123"}]

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

        result = await test_repo.exists("123")

        assert result is True

    async def test_exists_deleted_record(self, test_repo, mock_db_client):
        """Check if deleted record exists (should return False)."""
        mock_result = MagicMock()
        mock_result.data = None

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

        result = await test_repo.exists("123")

        assert result is False

    async def test_count_active_records(self, test_repo, mock_db_client):
        """Count active records."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "1"}, {"id": "2"}, {"id": "3"}]

        mock_db_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        count = await test_repo.count()

        assert count == 3

    async def test_count_with_filters(self, test_repo, mock_db_client):
        """Count records with custom filters."""
        mock_result = MagicMock()
        mock_result.data = [{"id": "1"}, {"id": "2"}]

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        count = await test_repo.count(filters={"user_id": "user_123"})

        assert count == 2


# ==========================================
# Integration Tests
# ==========================================

@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for common workflows."""

    async def test_soft_delete_and_restore_workflow(self, test_repo, mock_db_client):
        """Test soft delete → restore workflow."""
        # Mock recovery period config
        test_repo._get_recovery_period_days = AsyncMock(return_value=30)

        # Soft delete
        mock_result_delete = MagicMock()
        mock_result_delete.data = [{"id": "123"}]
        mock_db_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result_delete

        deleted = await test_repo.soft_delete("123")
        assert deleted is True

        # Restore
        mock_result_restore = MagicMock()
        mock_result_restore.data = [{"id": "123"}]
        mock_db_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result_restore

        restored = await test_repo.restore("123")
        assert restored is True

    async def test_soft_delete_to_permanent_workflow(self, test_repo, mock_db_client):
        """Test soft delete → permanent delete workflow."""
        # Mock recovery period config
        test_repo._get_recovery_period_days = AsyncMock(return_value=30)

        # Soft delete first
        mock_result_soft = MagicMock()
        mock_result_soft.data = [{"id": "123"}]
        mock_db_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result_soft

        soft_deleted = await test_repo.soft_delete("123")
        assert soft_deleted is True

        # Then permanently delete
        test_repo._supports_permanent_delete_flag = AsyncMock(return_value=True)
        mock_result_hard = MagicMock()
        mock_result_hard.data = [{"id": "123"}]
        mock_db_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result_hard

        permanently_deleted = await test_repo.hard_delete("123")
        assert permanently_deleted is True

# ==========================================
# Recovery Period Tests
# ==========================================

@pytest.mark.asyncio
class TestRecoveryPeriod:
    """Tests for recovery period expiry functionality."""

    async def test_get_recovery_period_days_success(self, test_repo, mock_db_client):
        """Successfully get recovery period from config."""
        # Mock config table response
        mock_result = MagicMock()
        mock_result.data = {"config_value": "45"}
        mock_db_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

        # Execute
        days = await test_repo._get_recovery_period_days()

        # Assert
        assert days == 45
        mock_db_client.table.assert_called_with("system_configs")

    async def test_get_recovery_period_days_default_on_error(self, test_repo, mock_db_client):
        """Return default 30 days when config read fails."""
        # Mock database error
        mock_db_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("DB error")

        # Execute
        days = await test_repo._get_recovery_period_days()

        # Assert default value
        assert days == 30

    async def test_soft_delete_with_recovery_expiry(self, test_repo, mock_db_client):
        """Soft delete should set recovery_expires_at."""
        # Mock config response
        test_repo._get_recovery_period_days = AsyncMock(return_value=30)

        # Mock successful deletion
        mock_result = MagicMock()
        mock_result.data = [{"id": "123", "is_deleted": True}]
        mock_db_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        # Execute
        result = await test_repo.soft_delete("123")

        # Assert
        assert result is True

        # Verify update call includes recovery_expires_at
        update_call = mock_db_client.table.return_value.update.call_args[0][0]
        assert "recovery_expires_at" in update_call
        assert update_call["is_deleted"] is True
        assert "deleted_at" in update_call

        # Verify recovery_expires_at is ~30 days from now
        recovery_time = datetime.fromisoformat(update_call["recovery_expires_at"].replace('Z', '+00:00'))
        deleted_time = datetime.fromisoformat(update_call["deleted_at"].replace('Z', '+00:00'))
        delta = recovery_time - deleted_time
        assert 29 <= delta.days <= 30  # Allow for timing variance

    async def test_restore_clears_recovery_expiry(self, test_repo, mock_db_client):
        """Restore should clear recovery_expires_at."""
        # Mock successful restore
        mock_result = MagicMock()
        mock_result.data = [{"id": "123"}]
        mock_db_client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        # Execute
        result = await test_repo.restore("123")

        # Assert
        assert result is True

        # Verify update call clears recovery_expires_at
        update_call = mock_db_client.table.return_value.update.call_args[0][0]
        assert update_call["is_deleted"] is False
        assert update_call["deleted_at"] is None
        assert update_call["recovery_expires_at"] is None

    async def test_list_deleted_recoverable_success(self, test_repo, mock_db_client):
        """List only recoverable deleted records (not expired)."""
        # Mock query result with 2 recoverable records
        mock_result = MagicMock()
        mock_result.data = [
            {"id": "123", "name": "Record 1"},
            {"id": "456", "name": "Record 2"}
        ]
        mock_result.count = 2

        # Setup mock chain
        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        # Execute
        entities, total = await test_repo.list_deleted_recoverable(
            user_id="user_789",
            offset=0,
            limit=20
        )

        # Assert
        assert len(entities) == 2
        assert total == 2
        assert entities[0].id == "123"
        assert entities[1].id == "456"

        # Verify query filters
        mock_db_client.table.assert_called_with("test_table")
        # Verify it filters by user_id, is_deleted=true, and recovery_expires_at > NOW()

    async def test_list_deleted_recoverable_empty(self, test_repo, mock_db_client):
        """List returns empty when no recoverable records."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        # Execute
        entities, total = await test_repo.list_deleted_recoverable(
            user_id="user_789",
            offset=0,
            limit=20
        )

        # Assert
        assert len(entities) == 0
        assert total == 0

    async def test_soft_delete_with_custom_recovery_period(self, test_repo, mock_db_client):
        """Soft delete uses custom recovery period from config."""
        # Mock config with 60 days
        test_repo._get_recovery_period_days = AsyncMock(return_value=60)

        # Mock successful deletion
        mock_result = MagicMock()
        mock_result.data = [{"id": "123"}]
        mock_db_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        # Execute
        result = await test_repo.soft_delete("123")

        # Assert
        assert result is True

        # Verify recovery period is ~60 days
        update_call = mock_db_client.table.return_value.update.call_args[0][0]
        recovery_time = datetime.fromisoformat(update_call["recovery_expires_at"].replace('Z', '+00:00'))
        deleted_time = datetime.fromisoformat(update_call["deleted_at"].replace('Z', '+00:00'))
        delta = recovery_time - deleted_time
        assert 59 <= delta.days <= 60

    async def test_list_deleted_recoverable_pagination(self, test_repo, mock_db_client):
        """List deleted recoverable supports pagination."""
        # Mock paginated result
        mock_result = MagicMock()
        mock_result.data = [{"id": f"{i}", "name": f"Record {i}"} for i in range(10, 20)]
        mock_result.count = 50  # Total count

        mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        # Execute with offset=10, limit=10
        entities, total = await test_repo.list_deleted_recoverable(
            user_id="user_789",
            offset=10,
            limit=10
        )

        # Assert
        assert len(entities) == 10
        assert total == 50
        assert entities[0].id == "10"

        # Verify range call
        mock_range = mock_db_client.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.order.return_value.range
        mock_range.assert_called_once_with(10, 19)  # offset to offset+limit-1
