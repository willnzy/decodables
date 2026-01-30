"""
AI Usage Tracker Tests
AI 使用量追踪测试

核心业务规则:
1. 异步追踪 AI 调用
2. 成本估算
3. 按日汇总
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal


# ==========================================
# Fixtures
# ==========================================

@pytest.fixture(autouse=True)
def mock_config_service():
    """Mock _get_config_service to prevent ConfigRepository instantiation."""
    with patch('shared.ai.model_config._get_config_service') as mock_get_service:
        mock_service = MagicMock()
        mock_service.get_config = AsyncMock(return_value=None)
        mock_get_service.return_value = mock_service
        yield mock_service


class TestEstimateCost:
    @pytest.mark.asyncio
    @patch('shared.ai.usage_tracker.get_model_cost', new_callable=AsyncMock)
    async def test_text_cost_calculation(self, mock_get_cost):
        from shared.ai.usage_tracker import _estimate_cost
        mock_get_cost.return_value = 1.0  # $1 per 1M tokens

        cost = await _estimate_cost(
            provider="openai",
            model="gpt-4o-mini",
            call_type="text",
            input_tokens=500,
            output_tokens=500
        )

        # 1000 tokens at $1/1M = $0.001
        assert cost == Decimal("0.0010")

    @pytest.mark.asyncio
    @patch('shared.ai.usage_tracker.get_model_cost', new_callable=AsyncMock)
    async def test_image_cost_calculation(self, mock_get_cost):
        from shared.ai.usage_tracker import _estimate_cost
        mock_get_cost.return_value = 0.04  # $0.04 per image

        cost = await _estimate_cost(
            provider="fal",
            model="flux-schnell",
            call_type="image",
            images=5
        )

        assert cost == Decimal("0.2000")

    @pytest.mark.asyncio
    @patch('shared.ai.usage_tracker.get_model_cost', new_callable=AsyncMock)
    async def test_cost_precision(self, mock_get_cost):
        from shared.ai.usage_tracker import _estimate_cost
        mock_get_cost.return_value = 0.50

        cost = await _estimate_cost(
            provider="openai",
            model="gpt-4o",
            call_type="text",
            input_tokens=123,
            output_tokens=456
        )

        # Should have 4 decimal places
        assert str(cost).count('.') <= 1
        places = len(str(cost).split('.')[-1]) if '.' in str(cost) else 0
        assert places <= 4


class TestTrackAIUsageSync:
    @patch('shared.ai.usage_tracker.supabase')
    @patch('shared.ai.usage_tracker.asyncio.run')
    def test_tracks_usage_successfully(self, mock_asyncio_run, mock_supabase):
        from shared.ai.usage_tracker import track_ai_usage_sync
        # Mock asyncio.run to return the Decimal directly
        mock_asyncio_run.return_value = Decimal("0.0010")

        track_ai_usage_sync(
            provider="openai",
            model="gpt-4o-mini",
            call_type="text",
            success=True,
            input_tokens=500,
            output_tokens=500
        )

        mock_supabase.rpc.assert_called_once()
        mock_asyncio_run.assert_called_once()

    @patch('shared.ai.usage_tracker.supabase', None)
    @patch('shared.ai.usage_tracker.asyncio.run')
    def test_handles_no_supabase(self, mock_asyncio_run):
        from shared.ai.usage_tracker import track_ai_usage_sync
        mock_asyncio_run.return_value = Decimal("0.0010")

        # Should not raise
        track_ai_usage_sync(
            provider="openai",
            model="gpt-4o-mini",
            call_type="text",
            success=True
        )

    @patch('shared.ai.usage_tracker.supabase')
    @patch('shared.ai.usage_tracker.asyncio.run')
    def test_handles_exception(self, mock_asyncio_run, mock_supabase):
        from shared.ai.usage_tracker import track_ai_usage_sync
        mock_asyncio_run.return_value = Decimal("0.0010")
        mock_supabase.rpc.side_effect = Exception("DB Error")

        # Should not raise
        track_ai_usage_sync(
            provider="openai",
            model="gpt-4o-mini",
            call_type="text",
            success=True
        )


class TestTrackAIUsageAsync:
    @pytest.mark.asyncio
    @patch('shared.ai.usage_tracker.supabase')
    @patch('shared.ai.usage_tracker._estimate_cost', new_callable=AsyncMock)
    async def test_tracks_usage_async(self, mock_cost, mock_supabase):
        from shared.ai.usage_tracker import track_ai_usage
        mock_cost.return_value = Decimal("0.0010")
        
        # Mock the RPC call
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value = MagicMock()
        mock_supabase.rpc.return_value = mock_rpc
        
        await track_ai_usage(
            provider="openai",
            model="gpt-4o-mini",
            call_type="text",
            success=True,
            input_tokens=500,
            output_tokens=500
        )

    @pytest.mark.asyncio
    @patch('shared.ai.usage_tracker.supabase', None)
    @patch('shared.ai.usage_tracker._estimate_cost')
    async def test_handles_no_supabase_async(self, mock_cost):
        from shared.ai.usage_tracker import track_ai_usage
        mock_cost.return_value = Decimal("0.0010")
        
        # Should not raise
        await track_ai_usage(
            provider="openai",
            model="gpt-4o-mini",
            call_type="text",
            success=True
        )


class TestGetUsageSummary:
    @patch('shared.ai.usage_tracker.supabase', None)
    def test_returns_empty_when_no_db(self):
        from shared.ai.usage_tracker import get_usage_summary
        result = get_usage_summary()
        assert result == {}

    @patch('shared.ai.usage_tracker.supabase')
    def test_returns_summary(self, mock_supabase):
        from shared.ai.usage_tracker import get_usage_summary
        
        # Source uses supabase.schema("internal").from_(...), so mock the full chain
        mock_supabase.schema.return_value.from_.return_value.select.return_value.execute.return_value.data = [
            {"provider": "openai", "model": "gpt-4o", "total_calls": 100, "total_cost_usd": 5.0},
            {"provider": "openai", "model": "gpt-4o-mini", "total_calls": 200, "total_cost_usd": 1.0},
        ]
        
        result = get_usage_summary()
        
        assert result["total_calls"] == 300
        assert result["total_cost_usd"] == 6.0
        assert "openai" in result["by_provider"]

    @patch('shared.ai.usage_tracker.supabase')
    def test_returns_empty_on_no_data(self, mock_supabase):
        from shared.ai.usage_tracker import get_usage_summary
        # Source uses supabase.schema("internal").from_(...), so mock the full chain
        mock_supabase.schema.return_value.from_.return_value.select.return_value.execute.return_value.data = None
        
        result = get_usage_summary()
        
        assert result["total_calls"] == 0

    @patch('shared.ai.usage_tracker.supabase')
    def test_handles_exception(self, mock_supabase):
        from shared.ai.usage_tracker import get_usage_summary
        # Source uses supabase.schema("internal").from_(...), so trigger on schema()
        mock_supabase.schema.return_value.from_.side_effect = Exception("DB Error")
        
        result = get_usage_summary()
        
        assert result == {}


class TestGetDailyTrend:
    @patch('shared.ai.usage_tracker.supabase', None)
    def test_returns_empty_when_no_db(self):
        from shared.ai.usage_tracker import get_daily_trend
        result = get_daily_trend()
        assert result == []

    @patch('shared.ai.usage_tracker.supabase')
    def test_returns_trend_data(self, mock_supabase):
        from shared.ai.usage_tracker import get_daily_trend
        
        mock_supabase.from_.return_value.select.return_value.execute.return_value.data = [
            {"date": "2025-01-01", "cost_usd": 5.23, "calls": 456},
            {"date": "2025-01-02", "cost_usd": 4.56, "calls": 345},
        ]
        
        result = get_daily_trend()
        
        assert len(result) == 2
        assert result[0]["date"] == "2025-01-01"

    @patch('shared.ai.usage_tracker.supabase')
    def test_handles_exception(self, mock_supabase):
        from shared.ai.usage_tracker import get_daily_trend
        mock_supabase.from_.side_effect = Exception("DB Error")
        
        result = get_daily_trend()
        
        assert result == []
