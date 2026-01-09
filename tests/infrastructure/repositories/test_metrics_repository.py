"""
Tests for MetricsRepository

@module tests.infrastructure.repositories.test_metrics_repository
@version 3.28

v3.28: Comprehensive tests for MetricsRepository (MET-LOW-3)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from infrastructure.repositories.metrics_repository import SupabaseMetricsRepository


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def mock_db_client():
    """Create mock Supabase client."""
    client = MagicMock()
    return client


@pytest.fixture
def metrics_repo(mock_db_client):
    """Create MetricsRepository instance."""
    return SupabaseMetricsRepository(mock_db_client)


# ==========================================
# get_daily_metrics Tests
# ==========================================

@pytest.mark.asyncio
class TestGetDailyMetrics:
    """Tests for get_daily_metrics method."""

    async def test_get_daily_metrics_success(self, metrics_repo, mock_db_client):
        """Successfully retrieve daily metrics."""
        # Mock data
        mock_result = MagicMock()
        mock_result.data = [
            {"date": "2026-01-08", "dau": 100, "mau": 500},
            {"date": "2026-01-09", "dau": 120, "mau": 520},
        ]

        # Setup mock chain
        mock_db_client.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        # Execute
        result = await metrics_repo.get_daily_metrics("2026-01-08", "2026-01-09")

        # Assert
        assert len(result) == 2
        assert result[0]["date"] == "2026-01-08"
        assert result[0]["dau"] == 100
        assert result[1]["date"] == "2026-01-09"
        assert result[1]["dau"] == 120

        # Verify call chain
        mock_db_client.table.assert_called_once_with("daily_metrics")
        mock_db_client.table.return_value.select.return_value.gte.assert_called_once_with("date", "2026-01-08")
        mock_db_client.table.return_value.select.return_value.gte.return_value.lte.assert_called_once_with("date", "2026-01-09")
        mock_db_client.table.return_value.select.return_value.gte.return_value.lte.return_value.order.assert_called_once_with("date")
        mock_db_client.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value.limit.assert_called_once_with(366)

    async def test_get_daily_metrics_empty_result(self, metrics_repo, mock_db_client):
        """Handle empty result."""
        mock_result = MagicMock()
        mock_result.data = None

        mock_db_client.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        result = await metrics_repo.get_daily_metrics("2026-01-01", "2026-01-02")

        assert result == []

    async def test_get_daily_metrics_custom_limit(self, metrics_repo, mock_db_client):
        """Respect custom limit parameter."""
        mock_result = MagicMock()
        mock_result.data = []

        mock_db_client.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        await metrics_repo.get_daily_metrics("2026-01-01", "2026-01-02", limit=100)

        mock_db_client.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value.limit.assert_called_once_with(100)


# ==========================================
# get_monthly_metrics Tests
# ==========================================

@pytest.mark.asyncio
class TestGetMonthlyMetrics:
    """Tests for get_monthly_metrics method."""

    async def test_get_monthly_metrics_success(self, metrics_repo, mock_db_client):
        """Successfully retrieve monthly metrics."""
        mock_result = MagicMock()
        mock_result.data = [
            {"month": "2026-01", "total_users": 1000},
            {"month": "2025-12", "total_users": 950},
        ]

        mock_db_client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        result = await metrics_repo.get_monthly_metrics(6)

        assert len(result) == 2
        assert result[0]["month"] == "2026-01"
        mock_db_client.table.assert_called_once_with("monthly_metrics")
        mock_db_client.table.return_value.select.return_value.order.assert_called_once_with("month", desc=True)
        mock_db_client.table.return_value.select.return_value.order.return_value.limit.assert_called_once_with(6)


# ==========================================
# get_retention_metrics Tests
# ==========================================

@pytest.mark.asyncio
class TestGetRetentionMetrics:
    """Tests for get_retention_metrics method."""

    async def test_get_retention_metrics_success(self, metrics_repo, mock_db_client):
        """Successfully retrieve retention metrics."""
        mock_result = MagicMock()
        mock_result.data = [
            {"data": {"day_1": 80.5, "day_7": 60.2, "day_30": 40.1}}
        ]

        mock_db_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        result = await metrics_repo.get_retention_metrics()

        assert result == {"day_1": 80.5, "day_7": 60.2, "day_30": 40.1}
        mock_db_client.table.assert_called_once_with("aggregated_stats")
        mock_db_client.table.return_value.select.assert_called_once_with("data")
        mock_db_client.table.return_value.select.return_value.eq.assert_called_once_with("stat_type", "user_retention_30d")

    async def test_get_retention_metrics_no_data(self, metrics_repo, mock_db_client):
        """Handle no retention data."""
        mock_result = MagicMock()
        mock_result.data = []

        mock_db_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        result = await metrics_repo.get_retention_metrics()

        assert result is None


# ==========================================
# get_funnel_counts Tests
# ==========================================

@pytest.mark.asyncio
class TestGetFunnelCounts:
    """Tests for get_funnel_counts method."""

    async def test_get_funnel_counts_success(self, metrics_repo, mock_db_client):
        """Successfully retrieve funnel counts with time filter."""
        # Mock results for each event type
        def mock_execute_for_event(event_type_value):
            """Create mock result based on event type."""
            mock_result = MagicMock()
            counts = {
                "page_view": 1000,
                "user_created": 500,
                "project_create": 300,
            }
            mock_result.count = counts.get(event_type_value, 0)
            return mock_result

        # Setup mock to return different counts for different event types
        call_count = [0]
        event_types = ["page_view", "user_created", "project_create"]

        def execute_side_effect():
            result = mock_execute_for_event(event_types[call_count[0]])
            call_count[0] += 1
            return result

        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.side_effect = execute_side_effect

        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        result = await metrics_repo.get_funnel_counts(event_types, cutoff_date)

        assert result["page_view"] == 1000
        assert result["user_created"] == 500
        assert result["project_create"] == 300
        assert mock_db_client.table.return_value.select.return_value.eq.return_value.gte.call_count == 3

    async def test_get_funnel_counts_with_time_filter(self, metrics_repo, mock_db_client):
        """Verify time filter is applied."""
        mock_result = MagicMock()
        mock_result.count = 100

        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_result

        cutoff_date = "2026-01-01T00:00:00"
        await metrics_repo.get_funnel_counts(["page_view"], cutoff_date)

        # Verify gte was called with cutoff_date
        mock_db_client.table.return_value.select.return_value.eq.return_value.gte.assert_called_with("created_at", cutoff_date)


# ==========================================
# get_error_stats Tests
# ==========================================

@pytest.mark.asyncio
class TestGetErrorStats:
    """Tests for get_error_stats method."""

    async def test_get_error_stats_success(self, metrics_repo, mock_db_client):
        """Successfully retrieve error statistics."""
        mock_result = MagicMock()
        mock_result.data = [
            {"error_type": "ValidationError", "status_code": 400},
            {"error_type": "ValidationError", "status_code": 400},
            {"error_type": "ServerError", "status_code": 500},
        ]

        mock_db_client.table.return_value.select.return_value.gte.return_value.limit.return_value.execute.return_value = mock_result

        result = await metrics_repo.get_error_stats(24)

        assert result["total"] == 3
        assert result["by_type"]["ValidationError"] == 2
        assert result["by_type"]["ServerError"] == 1
        assert result["by_status"][400] == 2
        assert result["by_status"][500] == 1

        mock_db_client.table.assert_called_once_with("error_logs")
        mock_db_client.table.return_value.select.return_value.gte.return_value.limit.assert_called_once_with(10000)

    async def test_get_error_stats_empty(self, metrics_repo, mock_db_client):
        """Handle no error data."""
        mock_result = MagicMock()
        mock_result.data = []

        mock_db_client.table.return_value.select.return_value.gte.return_value.limit.return_value.execute.return_value = mock_result

        result = await metrics_repo.get_error_stats(24)

        assert result["total"] == 0
        assert result["by_type"] == {}
        assert result["by_status"] == {}

    async def test_get_error_stats_custom_limit(self, metrics_repo, mock_db_client):
        """Respect custom limit parameter."""
        mock_result = MagicMock()
        mock_result.data = []

        mock_db_client.table.return_value.select.return_value.gte.return_value.limit.return_value.execute.return_value = mock_result

        await metrics_repo.get_error_stats(48, limit=5000)

        mock_db_client.table.return_value.select.return_value.gte.return_value.limit.assert_called_once_with(5000)


# ==========================================
# get_dau_trend Tests
# ==========================================

@pytest.mark.asyncio
class TestGetDAUTrend:
    """Tests for get_dau_trend method."""

    async def test_get_dau_trend_success(self, metrics_repo, mock_db_client):
        """Successfully retrieve DAU trend."""
        mock_result = MagicMock()
        mock_result.data = [
            {"date": "2026-01-09", "dau": 150},
            {"date": "2026-01-08", "dau": 140},
        ]

        mock_db_client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        result = await metrics_repo.get_dau_trend(30)

        assert len(result) == 2
        assert result[0]["date"] == "2026-01-09"
        assert result[0]["dau"] == 150

        mock_db_client.table.assert_called_once_with("daily_metrics")
        mock_db_client.table.return_value.select.assert_called_once_with("date, dau")
        mock_db_client.table.return_value.select.return_value.order.assert_called_once_with("date", desc=True)
        mock_db_client.table.return_value.select.return_value.order.return_value.limit.assert_called_once_with(30)
