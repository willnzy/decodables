"""
Webhook Repository Tests (P3-022)
Webhook 仓储层单元测试 - Mock Supabase

Coverage target: 85%+
Infrastructure logic tested:
- Supabase client calls (insert, update, select)
- Idempotent event creation (duplicate key handling)
- Retry count increment (fetch-then-increment pattern)
- Failed webhooks query (filters, pagination)
- Error handling and graceful degradation

创建时间: 2026-01-11
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta

from infrastructure.repositories.webhook_repository import SupabaseWebhookRepository


class TestSupabaseWebhookRepository:
    """Test SupabaseWebhookRepository infrastructure layer"""

    @pytest.fixture
    def mock_client(self):
        """Create mock Supabase client"""
        return MagicMock()

    @pytest.fixture
    def repository(self, mock_client):
        """Create repository with mock client"""
        return SupabaseWebhookRepository(client=mock_client)

    # ==========================================
    # Stripe Webhook Events Tests
    # ==========================================

    @pytest.mark.asyncio
    async def test_create_stripe_webhook_event_success(self, repository, mock_client):
        """create_stripe_webhook_event inserts event successfully"""
        # Mock response
        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": 1,
                "event_id": "evt_test_123",
                "event_type": "checkout.session.completed",
                "payload": {"data": "test"},
                "processed": False,
                "retry_count": 0,
                "created_at": "2026-01-11T10:00:00Z"
            }
        ]

        # Setup mock chain
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result

        # Execute
        result = await repository.create_stripe_webhook_event(
            event_id="evt_test_123",
            event_type="checkout.session.completed",
            payload={"data": "test"}
        )

        # Verify
        mock_client.table.assert_called_once_with("stripe_webhook_events")
        mock_client.table.return_value.insert.assert_called_once_with(
            {
                "event_id": "evt_test_123",
                "event_type": "checkout.session.completed",
                "payload": {"data": "test"},
                "processed": False,
                "retry_count": 0,
            },
            upsert=False
        )
        assert result["event_id"] == "evt_test_123"
        assert result["processed"] is False

    @pytest.mark.asyncio
    async def test_create_stripe_webhook_event_duplicate_key(self, repository, mock_client):
        """create_stripe_webhook_event handles duplicate event_id gracefully"""
        # Mock duplicate key error
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )

        # Execute
        result = await repository.create_stripe_webhook_event(
            event_id="evt_duplicate_123",
            event_type="checkout.session.completed",
            payload={"data": "test"}
        )

        # Verify idempotency - returns None for duplicates
        assert result is None

    @pytest.mark.asyncio
    async def test_update_stripe_webhook_status_success(self, repository, mock_client):
        """update_stripe_webhook_status marks event as processed"""
        # Mock response
        mock_result = MagicMock()
        mock_result.data = [{"event_id": "evt_123", "processed": True}]

        # Setup mock chain
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result

        # Execute
        success = await repository.update_stripe_webhook_status(
            event_id="evt_123",
            processed=True,
            error_message=None,
            increment_retry=False
        )

        # Verify
        assert success is True
        mock_client.table.return_value.update.assert_called_once()
        update_call_args = mock_client.table.return_value.update.call_args[0][0]
        assert update_call_args["processed"] is True
        assert update_call_args["error_message"] is None

    @pytest.mark.asyncio
    async def test_update_stripe_webhook_status_with_retry_increment(self, repository, mock_client):
        """update_stripe_webhook_status increments retry_count (fetch-then-increment)"""
        # Mock current retry_count fetch
        mock_fetch_result = MagicMock()
        mock_fetch_result.data = {"retry_count": 2}

        # Mock update result
        mock_update_result = MagicMock()
        mock_update_result.data = [{"event_id": "evt_123", "retry_count": 3}]

        # Setup mock chain for fetch
        mock_select_chain = mock_client.table.return_value.select.return_value
        mock_select_chain.eq.return_value.single.return_value.execute.return_value = mock_fetch_result

        # Setup mock chain for update
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_result

        # Execute
        success = await repository.update_stripe_webhook_status(
            event_id="evt_123",
            processed=False,
            error_message="Connection timeout",
            increment_retry=True
        )

        # Verify fetch-then-increment pattern
        assert success is True
        mock_client.table.return_value.select.assert_called_with("retry_count")

        # Verify update with incremented value
        update_call_args = mock_client.table.return_value.update.call_args[0][0]
        assert update_call_args["retry_count"] == 3  # 2 + 1
        assert update_call_args["processed"] is False
        assert update_call_args["error_message"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_get_failed_stripe_webhooks_with_filters(self, repository, mock_client):
        """get_failed_stripe_webhooks applies correct filters and pagination"""
        # Mock response
        mock_result = MagicMock()
        mock_result.data = [
            {
                "event_id": "evt_failed_1",
                "event_type": "checkout.session.completed",
                "retry_count": 2,
                "error_message": "Timeout",
                "created_at": "2026-01-11T08:00:00Z"
            },
            {
                "event_id": "evt_failed_2",
                "event_type": "invoice.payment_succeeded",
                "retry_count": 1,
                "error_message": "Network error",
                "created_at": "2026-01-11T09:00:00Z"
            }
        ]

        # Setup mock chain
        mock_query = mock_client.table.return_value.select.return_value
        mock_query.eq.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.order.return_value.limit.return_value.execute.return_value = mock_result

        # Execute
        result = await repository.get_failed_stripe_webhooks(
            max_retry_count=5,
            hours_since_created=72,
            limit=50
        )

        # Verify filters applied
        assert len(result) == 2
        mock_query.eq.assert_called_with("processed", False)
        mock_query.lt.assert_called_with("retry_count", 5)
        # gte called with cutoff_time (72 hours ago)

    @pytest.mark.asyncio
    async def test_get_failed_stripe_webhooks_error_handling(self, repository, mock_client):
        """get_failed_stripe_webhooks returns empty list on error"""
        # Mock error
        mock_client.table.return_value.select.side_effect = Exception("Database error")

        # Execute
        result = await repository.get_failed_stripe_webhooks()

        # Verify graceful degradation
        assert result == []

    # ==========================================
    # Clerk Webhook Events Tests
    # ==========================================

    @pytest.mark.asyncio
    async def test_create_clerk_webhook_event_success(self, repository, mock_client):
        """create_clerk_webhook_event inserts event successfully"""
        # Mock response
        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": 1,
                "event_id": "evt_clerk_123",
                "event_type": "user.created",
                "payload": {"data": "test"},
                "processed": False,
                "retry_count": 0
            }
        ]

        # Setup mock chain
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_result

        # Execute
        result = await repository.create_clerk_webhook_event(
            event_id="evt_clerk_123",
            event_type="user.created",
            payload={"data": "test"}
        )

        # Verify
        mock_client.table.assert_called_with("clerk_webhook_events")
        assert result["event_id"] == "evt_clerk_123"

    @pytest.mark.asyncio
    async def test_create_clerk_webhook_event_duplicate_key(self, repository, mock_client):
        """create_clerk_webhook_event handles duplicate gracefully"""
        # Mock duplicate key error
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception(
            "duplicate key constraint"
        )

        # Execute
        result = await repository.create_clerk_webhook_event(
            event_id="evt_clerk_duplicate",
            event_type="user.created",
            payload={"data": "test"}
        )

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_update_clerk_webhook_status_with_retry_increment(self, repository, mock_client):
        """update_clerk_webhook_status increments retry_count correctly"""
        # Mock fetch result
        mock_fetch_result = MagicMock()
        mock_fetch_result.data = {"retry_count": 1}

        # Mock update result
        mock_update_result = MagicMock()
        mock_update_result.data = [{"retry_count": 2}]

        # Setup mock chains
        mock_select_chain = mock_client.table.return_value.select.return_value
        mock_select_chain.eq.return_value.single.return_value.execute.return_value = mock_fetch_result
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_result

        # Execute
        success = await repository.update_clerk_webhook_status(
            event_id="evt_clerk_123",
            processed=False,
            error_message="Retry",
            increment_retry=True
        )

        # Verify
        assert success is True
        update_call_args = mock_client.table.return_value.update.call_args[0][0]
        assert update_call_args["retry_count"] == 2

    @pytest.mark.asyncio
    async def test_get_failed_clerk_webhooks_pagination(self, repository, mock_client):
        """get_failed_clerk_webhooks respects limit parameter"""
        # Mock response with many results
        mock_result = MagicMock()
        mock_result.data = [{"event_id": f"evt_{i}"} for i in range(100)]

        # Setup mock chain
        mock_query = mock_client.table.return_value.select.return_value
        mock_query.eq.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.order.return_value.limit.return_value.execute.return_value = mock_result

        # Execute with limit=10
        result = await repository.get_failed_clerk_webhooks(
            max_retry_count=5,
            hours_since_created=72,
            limit=10
        )

        # Verify limit applied
        mock_query.order.return_value.limit.assert_called_with(10)

    # ==========================================
    # Edge Cases and Error Handling
    # ==========================================

    @pytest.mark.asyncio
    async def test_update_status_with_zero_retry_count(self, repository, mock_client):
        """update_stripe_webhook_status handles retry_count=0 correctly"""
        # Mock fetch with retry_count=0
        mock_fetch_result = MagicMock()
        mock_fetch_result.data = {"retry_count": 0}

        mock_update_result = MagicMock()
        mock_update_result.data = [{"retry_count": 1}]

        # Setup mocks
        mock_select_chain = mock_client.table.return_value.select.return_value
        mock_select_chain.eq.return_value.single.return_value.execute.return_value = mock_fetch_result
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_result

        # Execute
        success = await repository.update_stripe_webhook_status(
            event_id="evt_new",
            processed=False,
            error_message="First failure",
            increment_retry=True
        )

        # Verify incremented from 0 to 1
        assert success is True
        update_call_args = mock_client.table.return_value.update.call_args[0][0]
        assert update_call_args["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_update_status_when_fetch_returns_none(self, repository, mock_client):
        """update_stripe_webhook_status defaults retry_count to 0 if fetch fails"""
        # Mock fetch returning None
        mock_fetch_result = MagicMock()
        mock_fetch_result.data = None

        mock_update_result = MagicMock()
        mock_update_result.data = [{"retry_count": 1}]

        # Setup mocks
        mock_select_chain = mock_client.table.return_value.select.return_value
        mock_select_chain.eq.return_value.single.return_value.execute.return_value = mock_fetch_result
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_result

        # Execute
        success = await repository.update_stripe_webhook_status(
            event_id="evt_missing",
            processed=False,
            error_message="Error",
            increment_retry=True
        )

        # Verify defaults to 0 + 1 = 1
        assert success is True
        update_call_args = mock_client.table.return_value.update.call_args[0][0]
        assert update_call_args["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_update_status_database_error(self, repository, mock_client):
        """update_stripe_webhook_status returns False on database error"""
        # Mock database error
        mock_client.table.return_value.update.side_effect = Exception("Database connection lost")

        # Execute
        success = await repository.update_stripe_webhook_status(
            event_id="evt_123",
            processed=True
        )

        # Verify graceful failure
        assert success is False

    @pytest.mark.asyncio
    async def test_get_failed_webhooks_filters_old_events(self, repository, mock_client):
        """get_failed_stripe_webhooks filters events older than max age"""
        # Mock response
        mock_result = MagicMock()
        mock_result.data = []

        mock_query = mock_client.table.return_value.select.return_value
        mock_query.eq.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.order.return_value.limit.return_value.execute.return_value = mock_result

        # Execute with hours_since_created=24
        await repository.get_failed_stripe_webhooks(
            max_retry_count=5,
            hours_since_created=24,
            limit=50
        )

        # Verify gte filter was called (cutoff time = now - 24 hours)
        # The actual cutoff_time is calculated dynamically, so we just verify the call
        assert mock_query.gte.called
