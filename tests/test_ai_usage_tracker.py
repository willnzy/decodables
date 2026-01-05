"""
AI Usage Tracker Tests
AI 使用量追踪器测试

Coverage target: 90%+
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from decimal import Decimal


class TestEstimateCost:
    """Test _estimate_cost function"""
    
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_text_model_cost(self, mock_get_cost):
        """Calculates cost for text model correctly"""
        from services.ai.usage_tracker import _estimate_cost
        
        mock_get_cost.return_value = 0.15  # $0.15 per 1M tokens
        
        cost = _estimate_cost(
            provider="openai",
            model="gpt-4o-mini",
            call_type="text",
            input_tokens=500,
            output_tokens=500,
        )
        
        # 1000 tokens * $0.15 / 1M = $0.00015
        assert cost == Decimal("0.0002")  # Rounded to 4 decimal places
    
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_image_model_cost(self, mock_get_cost):
        """Calculates cost for image model correctly"""
        from services.ai.usage_tracker import _estimate_cost
        
        mock_get_cost.return_value = 0.003  # $0.003 per image
        
        cost = _estimate_cost(
            provider="fal",
            model="flux-schnell",
            call_type="image",
            images=3,
        )
        
        # 3 images * $0.003 = $0.009
        assert cost == Decimal("0.0090")
    
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_zero_tokens_zero_cost(self, mock_get_cost):
        """Zero tokens means zero cost"""
        from services.ai.usage_tracker import _estimate_cost
        
        mock_get_cost.return_value = 0.15
        
        cost = _estimate_cost(
            provider="openai",
            model="gpt-4o",
            call_type="text",
            input_tokens=0,
            output_tokens=0,
        )
        
        assert cost == Decimal("0.0000")
    
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_zero_images_zero_cost(self, mock_get_cost):
        """Zero images means zero cost"""
        from services.ai.usage_tracker import _estimate_cost
        
        mock_get_cost.return_value = 0.05
        
        cost = _estimate_cost(
            provider="fal",
            model="flux-dev",
            call_type="image",
            images=0,
        )
        
        assert cost == Decimal("0.0000")


class TestTrackAiUsage:
    """Test track_ai_usage async function"""
    
    @patch('services.ai.usage_tracker.supabase')
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_tracks_successfully(self, mock_get_cost, mock_supabase):
        """Tracks usage successfully"""
        from services.ai.usage_tracker import track_ai_usage
        
        mock_get_cost.return_value = 0.15
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[{}])
        
        asyncio.get_event_loop().run_until_complete(
            track_ai_usage(
                provider="openai",
                model="gpt-4o-mini",
                call_type="text",
                success=True,
                input_tokens=100,
                output_tokens=200,
                latency_ms=500
            )
        )
        
        mock_supabase.rpc.assert_called()
    
    @patch('services.ai.usage_tracker.supabase', None)
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_handles_no_supabase(self, mock_get_cost):
        """Handles missing Supabase client gracefully"""
        from services.ai.usage_tracker import track_ai_usage
        
        mock_get_cost.return_value = 0.15
        
        # Should not raise
        asyncio.get_event_loop().run_until_complete(
            track_ai_usage(
                provider="openai",
                model="gpt-4o",
                call_type="text",
                success=True
            )
        )
    
    @patch('services.ai.usage_tracker.supabase')
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_handles_exception(self, mock_get_cost, mock_supabase):
        """Handles exception gracefully"""
        from services.ai.usage_tracker import track_ai_usage
        
        mock_get_cost.return_value = 0.15
        mock_supabase.rpc.side_effect = Exception("DB Error")
        
        # Should not raise
        asyncio.get_event_loop().run_until_complete(
            track_ai_usage(
                provider="openai",
                model="gpt-4o",
                call_type="text",
                success=False,
                error_type="api_error"
            )
        )
    
    @patch('services.ai.usage_tracker.supabase')
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_tracks_images(self, mock_get_cost, mock_supabase):
        """Tracks image generation usage"""
        from services.ai.usage_tracker import track_ai_usage
        
        mock_get_cost.return_value = 0.003
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[{}])
        
        asyncio.get_event_loop().run_until_complete(
            track_ai_usage(
                provider="fal",
                model="flux-schnell",
                call_type="image",
                success=True,
                images=3,
                latency_ms=5000
            )
        )


class TestTrackAiUsageSync:
    """Test track_ai_usage_sync function"""
    
    @patch('services.ai.usage_tracker.supabase')
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_tracks_successfully(self, mock_get_cost, mock_supabase):
        """Tracks usage synchronously"""
        from services.ai.usage_tracker import track_ai_usage_sync
        
        mock_get_cost.return_value = 0.15
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data=[{}])
        
        track_ai_usage_sync(
            provider="openai",
            model="gpt-4o-mini",
            call_type="text",
            success=True,
            input_tokens=100,
            output_tokens=200
        )
        
        mock_supabase.rpc.assert_called_once()
    
    @patch('services.ai.usage_tracker.supabase', None)
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_handles_no_supabase(self, mock_get_cost):
        """Handles missing Supabase client gracefully"""
        from services.ai.usage_tracker import track_ai_usage_sync
        
        mock_get_cost.return_value = 0.15
        
        # Should not raise
        track_ai_usage_sync(
            provider="openai",
            model="gpt-4o",
            call_type="text",
            success=True
        )
    
    @patch('services.ai.usage_tracker.supabase')
    @patch('services.ai.usage_tracker.get_model_cost')
    def test_handles_exception(self, mock_get_cost, mock_supabase):
        """Handles exception gracefully"""
        from services.ai.usage_tracker import track_ai_usage_sync
        
        mock_get_cost.return_value = 0.15
        mock_supabase.rpc.side_effect = Exception("DB Error")
        
        # Should not raise
        track_ai_usage_sync(
            provider="openai",
            model="gpt-4o",
            call_type="text",
            success=False,
            error_type="timeout"
        )


class TestGetUsageSummary:
    """Test get_usage_summary function"""
    
    @patch('services.ai.usage_tracker.supabase', None)
    def test_returns_empty_without_supabase(self):
        """Returns empty dict without Supabase"""
        from services.ai.usage_tracker import get_usage_summary
        
        result = get_usage_summary()
        
        assert result == {}
    
    @patch('services.ai.usage_tracker.supabase')
    def test_returns_empty_for_no_data(self, mock_supabase):
        """Returns empty summary for no data"""
        from services.ai.usage_tracker import get_usage_summary
        
        mock_supabase.from_.return_value.select.return_value.execute.return_value = MagicMock(
            data=None
        )
        
        result = get_usage_summary()
        
        assert result["total_calls"] == 0
        assert result["total_cost_usd"] == 0
    
    @patch('services.ai.usage_tracker.supabase')
    def test_returns_aggregated_data(self, mock_supabase):
        """Returns aggregated usage data"""
        from services.ai.usage_tracker import get_usage_summary
        
        mock_supabase.from_.return_value.select.return_value.execute.return_value = MagicMock(
            data=[
                {"provider": "openai", "model": "gpt-4o", "total_calls": 100, "total_cost_usd": 10.5},
                {"provider": "openai", "model": "gpt-4o-mini", "total_calls": 200, "total_cost_usd": 3.0},
                {"provider": "fal", "model": "flux-schnell", "total_calls": 50, "total_cost_usd": 0.15},
            ]
        )
        
        result = get_usage_summary()
        
        assert result["total_calls"] == 350
        assert result["total_cost_usd"] == 13.65
        assert result["by_provider"]["openai"]["calls"] == 300
        assert result["by_provider"]["fal"]["calls"] == 50
        assert result["by_model"]["gpt-4o"]["calls"] == 100
    
    @patch('services.ai.usage_tracker.supabase')
    def test_handles_exception(self, mock_supabase):
        """Handles exception gracefully"""
        from services.ai.usage_tracker import get_usage_summary
        
        mock_supabase.from_.side_effect = Exception("DB Error")
        
        result = get_usage_summary()
        
        assert result == {}


class TestGetDailyTrend:
    """Test get_daily_trend function"""
    
    @patch('services.ai.usage_tracker.supabase', None)
    def test_returns_empty_without_supabase(self):
        """Returns empty list without Supabase"""
        from services.ai.usage_tracker import get_daily_trend
        
        result = get_daily_trend()
        
        assert result == []
    
    @patch('services.ai.usage_tracker.supabase')
    def test_returns_trend_data(self, mock_supabase):
        """Returns daily trend data"""
        from services.ai.usage_tracker import get_daily_trend
        
        mock_supabase.from_.return_value.select.return_value.execute.return_value = MagicMock(
            data=[
                {"date": "2025-01-01", "cost_usd": 5.23, "calls": 100},
                {"date": "2025-01-02", "cost_usd": 6.12, "calls": 120},
            ]
        )
        
        result = get_daily_trend()
        
        assert len(result) == 2
        assert result[0]["date"] == "2025-01-01"
    
    @patch('services.ai.usage_tracker.supabase')
    def test_returns_empty_for_no_data(self, mock_supabase):
        """Returns empty list when no data"""
        from services.ai.usage_tracker import get_daily_trend
        
        mock_supabase.from_.return_value.select.return_value.execute.return_value = MagicMock(
            data=None
        )
        
        result = get_daily_trend()
        
        assert result == []
    
    @patch('services.ai.usage_tracker.supabase')
    def test_handles_exception(self, mock_supabase):
        """Handles exception gracefully"""
        from services.ai.usage_tracker import get_daily_trend
        
        mock_supabase.from_.side_effect = Exception("DB Error")
        
        result = get_daily_trend()
        
        assert result == []
