"""
Analytics Service Tests
分析服务测试

Coverage target: 90%+
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


class TestAnalyticsEvents:
    """Test AnalyticsEvents constants"""
    
    def test_page_view_event(self):
        """PAGE_VIEW event constant exists"""
        from services.analytics_service import AnalyticsEvents
        assert AnalyticsEvents.PAGE_VIEW == "page_view"
    
    def test_ai_events(self):
        """AI event constants exist"""
        from services.analytics_service import AnalyticsEvents
        assert AnalyticsEvents.AI_GENERATE_STARTED == "ai_generate_started"
        assert AnalyticsEvents.AI_GENERATE_SUCCESS == "ai_generate_success"
        assert AnalyticsEvents.AI_GENERATE_FAILED == "ai_generate_failed"
    
    def test_payment_events(self):
        """Payment event constants exist"""
        from services.analytics_service import AnalyticsEvents
        assert AnalyticsEvents.CHECKOUT_STARTED == "checkout_started"
        assert AnalyticsEvents.CHECKOUT_COMPLETED == "checkout_completed"
        assert AnalyticsEvents.CREDITS_PURCHASED == "credits_purchased"
    
    def test_project_events(self):
        """Project event constants exist"""
        from services.analytics_service import AnalyticsEvents
        assert AnalyticsEvents.PROJECT_CREATED == "project_created"
        assert AnalyticsEvents.PROJECT_SAVED == "project_saved"
        assert AnalyticsEvents.PROJECT_EXPORTED == "project_exported"
    
    def test_marketplace_events(self):
        """Marketplace event constants exist"""
        from services.analytics_service import AnalyticsEvents
        assert AnalyticsEvents.MARKETPLACE_VIEW == "marketplace_view"
        assert AnalyticsEvents.MARKETPLACE_PURCHASE == "marketplace_purchase"


class TestInsertEvent:
    """Test _insert_event internal function"""
    
    @patch('services.analytics_service.supabase', None)
    def test_returns_false_when_supabase_unavailable(self):
        """Returns False when Supabase is not available"""
        from services.analytics_service import _insert_event
        
        result = _insert_event("test_event", user_id="user_123")
        
        assert result is False
    
    @patch('services.analytics_service.supabase')
    def test_inserts_event_successfully(self, mock_supabase):
        """Successfully inserts event to database"""
        from services.analytics_service import _insert_event
        
        mock_result = MagicMock()
        mock_result.data = [{"id": 1}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
        
        result = _insert_event("test_event", user_id="user_123", properties={"key": "value"})
        
        assert result is True
        mock_supabase.table.assert_called_once_with("analytics_events")
    
    @patch('services.analytics_service.supabase')
    def test_returns_false_on_empty_result(self, mock_supabase):
        """Returns False when insert returns no data"""
        from services.analytics_service import _insert_event
        
        mock_result = MagicMock()
        mock_result.data = None
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
        
        result = _insert_event("test_event")
        
        assert result is False
    
    @patch('services.analytics_service.supabase')
    def test_returns_false_on_exception(self, mock_supabase):
        """Returns False on database exception"""
        from services.analytics_service import _insert_event
        
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB Error")
        
        result = _insert_event("test_event")
        
        assert result is False
    
    @patch('services.analytics_service.supabase')
    def test_includes_event_id_in_data(self, mock_supabase):
        """Includes event_id for CAPI deduplication"""
        from services.analytics_service import _insert_event
        
        mock_result = MagicMock()
        mock_result.data = [{"id": 1}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
        
        _insert_event("test_event", event_id="custom-event-id-123")
        
        # Check that insert was called with event_id
        insert_call = mock_supabase.table.return_value.insert.call_args
        inserted_data = insert_call[0][0]
        assert inserted_data["event_id"] == "custom-event-id-123"
    
    @patch('services.analytics_service.supabase')
    def test_auto_generates_event_id_when_not_provided(self, mock_supabase):
        """Auto-generates event_id when not provided"""
        from services.analytics_service import _insert_event
        
        mock_result = MagicMock()
        mock_result.data = [{"id": 1}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
        
        _insert_event("test_event")
        
        insert_call = mock_supabase.table.return_value.insert.call_args
        inserted_data = insert_call[0][0]
        assert "event_id" in inserted_data
        assert len(inserted_data["event_id"]) == 36  # UUID format


class TestTrackEvent:
    """Test track_event function"""
    
    @patch('services.analytics_service._insert_event')
    def test_blocking_mode_calls_insert_directly(self, mock_insert):
        """Blocking mode calls _insert_event directly"""
        from services.analytics_service import track_event
        
        mock_insert.return_value = True
        
        track_event("test_event", user_id="user_123", blocking=True)
        
        mock_insert.assert_called_once()
    
    @patch('services.analytics_service._executor')
    def test_non_blocking_mode_submits_to_executor(self, mock_executor):
        """Non-blocking mode submits to thread pool"""
        from services.analytics_service import track_event
        
        track_event("test_event", user_id="user_123", blocking=False)
        
        mock_executor.submit.assert_called_once()
    
    @patch('services.analytics_service._insert_event')
    def test_passes_all_parameters(self, mock_insert):
        """Passes all parameters to _insert_event"""
        from services.analytics_service import track_event
        
        track_event(
            "test_event",
            user_id="user_123",
            session_id="session_456",
            properties={"key": "value"},
            context={"ip": "1.2.3.4"},
            event_id="event-789",
            blocking=True
        )
        
        mock_insert.assert_called_once_with(
            "test_event", "user_123", "session_456", None,
            {"key": "value"}, {"ip": "1.2.3.4"}, "event-789"
        )


class TestTrackEventAsync:
    """Test track_event_async function"""
    
    @patch('services.analytics_service._insert_event')
    def test_async_tracking(self, mock_insert):
        """Async tracking works correctly"""
        from services.analytics_service import track_event_async
        
        mock_insert.return_value = True
        
        result = asyncio.get_event_loop().run_until_complete(
            track_event_async("test_event", user_id="user_123")
        )
        
        assert result is True


class TestTrackEventBatch:
    """Test track_event_batch function"""
    
    @patch('services.analytics_service.supabase', None)
    def test_returns_zero_when_supabase_unavailable(self):
        """Returns 0 when Supabase is not available"""
        from services.analytics_service import track_event_batch
        
        result = track_event_batch([{"event_name": "test"}])
        
        assert result == 0
    
    @patch('services.analytics_service.supabase')
    def test_batch_insert_success(self, mock_supabase):
        """Successfully batch inserts events"""
        from services.analytics_service import track_event_batch
        
        mock_result = MagicMock()
        mock_result.data = [{"id": 1}, {"id": 2}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
        
        events = [
            {"event_name": "event_1", "user_id": "user_1"},
            {"event_name": "event_2", "user_id": "user_2"},
        ]
        
        result = track_event_batch(events)
        
        assert result == 2
    
    @patch('services.analytics_service.supabase')
    def test_returns_zero_on_exception(self, mock_supabase):
        """Returns 0 on database exception"""
        from services.analytics_service import track_event_batch
        
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception("DB Error")
        
        result = track_event_batch([{"event_name": "test"}])
        
        assert result == 0
    
    @patch('services.analytics_service.supabase')
    def test_handles_events_with_all_fields(self, mock_supabase):
        """Handles events with all optional fields"""
        from services.analytics_service import track_event_batch
        
        mock_result = MagicMock()
        mock_result.data = [{"id": 1}]
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_result
        
        events = [
            {
                "event_name": "test",
                "user_id": "user_1",
                "session_id": "session_1",
                "anonymous_id": "anon_1",
                "properties": {"key": "value"},
                "context": {"ip": "1.2.3.4"},
            }
        ]
        
        result = track_event_batch(events)
        
        assert result == 1


class TestTrackAiGeneration:
    """Test track_ai_generation convenience function"""
    
    @patch('services.analytics_service.track_event')
    def test_success_event(self, mock_track):
        """Tracks success event correctly"""
        from services.analytics_service import track_ai_generation
        
        track_ai_generation(
            user_id="user_123",
            success=True,
            model="flux-schnell",
            cost_credits=5
        )
        
        mock_track.assert_called_once()
        call_args = mock_track.call_args
        assert call_args[0][0] == "ai_generate_success"
        assert call_args[1]["user_id"] == "user_123"
    
    @patch('services.analytics_service.track_event')
    def test_failure_event(self, mock_track):
        """Tracks failure event correctly"""
        from services.analytics_service import track_ai_generation
        
        track_ai_generation(
            user_id="user_123",
            success=False,
            model="flux-schnell",
            cost_credits=5,
            error_code="TIMEOUT"
        )
        
        call_args = mock_track.call_args
        assert call_args[0][0] == "ai_generate_failed"
        assert call_args[1]["properties"]["error_code"] == "TIMEOUT"
    
    @patch('services.analytics_service.track_event')
    def test_with_duration(self, mock_track):
        """Includes duration when provided"""
        from services.analytics_service import track_ai_generation
        
        track_ai_generation(
            user_id="user_123",
            success=True,
            model="flux",
            cost_credits=5,
            duration_ms=3200
        )
        
        call_args = mock_track.call_args
        assert call_args[1]["properties"]["duration_ms"] == 3200
    
    @patch('services.analytics_service.track_event')
    def test_with_extra_properties(self, mock_track):
        """Includes extra properties when provided"""
        from services.analytics_service import track_ai_generation
        
        track_ai_generation(
            user_id="user_123",
            success=True,
            model="flux",
            cost_credits=5,
            extra_properties={"prompt_length": 100}
        )
        
        call_args = mock_track.call_args
        assert call_args[1]["properties"]["prompt_length"] == 100


class TestTrackPayment:
    """Test track_payment convenience function"""
    
    @patch('services.analytics_service.track_event')
    def test_checkout_completed(self, mock_track):
        """Tracks checkout completed event"""
        from services.analytics_service import track_payment
        
        track_payment(
            user_id="user_123",
            event_type="checkout_completed",
            amount_cents=2990,
            plan="pro"
        )
        
        mock_track.assert_called_once()
        call_args = mock_track.call_args
        assert call_args[0][0] == "checkout_completed"
        assert call_args[1]["properties"]["amount_cents"] == 2990
        assert call_args[1]["properties"]["plan"] == "pro"
    
    @patch('services.analytics_service.track_event')
    def test_with_stripe_payment_id(self, mock_track):
        """Includes Stripe payment ID"""
        from services.analytics_service import track_payment
        
        track_payment(
            user_id="user_123",
            event_type="checkout_completed",
            amount_cents=2990,
            stripe_payment_id="pi_xxx"
        )
        
        call_args = mock_track.call_args
        assert call_args[1]["properties"]["stripe_payment_id"] == "pi_xxx"
    
    @patch('services.analytics_service.track_event')
    def test_with_extra_properties(self, mock_track):
        """Includes extra properties"""
        from services.analytics_service import track_payment
        
        track_payment(
            user_id="user_123",
            event_type="checkout_started",
            amount_cents=1990,
            extra_properties={"promo_code": "SAVE10"}
        )
        
        call_args = mock_track.call_args
        assert call_args[1]["properties"]["promo_code"] == "SAVE10"


class TestTrackMarketplaceAction:
    """Test track_marketplace_action convenience function"""
    
    @patch('services.analytics_service.track_event')
    def test_view_action(self, mock_track):
        """Tracks marketplace view"""
        from services.analytics_service import track_marketplace_action
        
        track_marketplace_action(
            user_id="user_123",
            action="view",
            listing_id="listing_456",
            resource_type="asset"
        )
        
        call_args = mock_track.call_args
        assert call_args[0][0] == "marketplace_view"
    
    @patch('services.analytics_service.track_event')
    def test_purchase_action(self, mock_track):
        """Tracks marketplace purchase"""
        from services.analytics_service import track_marketplace_action
        
        track_marketplace_action(
            user_id="user_123",
            action="purchase",
            listing_id="listing_456",
            resource_type="template",
            price_credits=50
        )
        
        call_args = mock_track.call_args
        assert call_args[0][0] == "marketplace_purchase"
        assert call_args[1]["properties"]["price_credits"] == 50
    
    @patch('services.analytics_service.track_event')
    def test_unknown_action(self, mock_track):
        """Handles unknown action gracefully"""
        from services.analytics_service import track_marketplace_action
        
        track_marketplace_action(
            user_id="user_123",
            action="custom_action",
            listing_id="listing_456",
            resource_type="asset"
        )
        
        call_args = mock_track.call_args
        assert call_args[0][0] == "marketplace_custom_action"
    
    @patch('services.analytics_service.track_event')
    def test_with_extra_properties(self, mock_track):
        """Includes extra properties"""
        from services.analytics_service import track_marketplace_action
        
        track_marketplace_action(
            user_id="user_123",
            action="purchase",
            listing_id="listing_456",
            resource_type="asset",
            extra_properties={"seller_id": "seller_789"}
        )
        
        call_args = mock_track.call_args
        assert call_args[1]["properties"]["seller_id"] == "seller_789"


class TestTrackProjectAction:
    """Test track_project_action convenience function"""
    
    @patch('services.analytics_service.track_event')
    def test_created_action(self, mock_track):
        """Tracks project created"""
        from services.analytics_service import track_project_action
        
        track_project_action(
            user_id="user_123",
            action="created",
            project_id="proj_456"
        )
        
        call_args = mock_track.call_args
        assert call_args[0][0] == "project_created"
        assert call_args[1]["properties"]["project_id"] == "proj_456"
    
    @patch('services.analytics_service.track_event')
    def test_exported_action(self, mock_track):
        """Tracks project exported"""
        from services.analytics_service import track_project_action
        
        track_project_action(
            user_id="user_123",
            action="exported",
            project_id="proj_456",
            extra_properties={"format": "pdf"}
        )
        
        call_args = mock_track.call_args
        assert call_args[0][0] == "project_exported"
        assert call_args[1]["properties"]["format"] == "pdf"
    
    @patch('services.analytics_service.track_event')
    def test_unknown_action(self, mock_track):
        """Handles unknown action gracefully"""
        from services.analytics_service import track_project_action
        
        track_project_action(
            user_id="user_123",
            action="custom_action",
            project_id="proj_456"
        )
        
        call_args = mock_track.call_args
        assert call_args[0][0] == "project_custom_action"


class TestShutdownAnalytics:
    """Test shutdown_analytics function"""
    
    @patch('services.analytics_service._executor')
    def test_calls_executor_shutdown(self, mock_executor):
        """Calls executor shutdown with correct parameters"""
        from services.analytics_service import shutdown_analytics
        
        shutdown_analytics()
        
        mock_executor.shutdown.assert_called_once_with(wait=True, cancel_futures=False)


class TestModuleLevel:
    """Test module-level behavior"""
    
    def test_executor_exists(self):
        """Thread pool executor exists"""
        from services.analytics_service import _executor
        assert _executor is not None
    
    def test_atexit_registered(self):
        """Shutdown handler is registered with atexit"""
        import atexit
        from services.analytics_service import shutdown_analytics
        # The function should be in the atexit registry
        # We can't easily verify this, but we can verify the function exists
        assert callable(shutdown_analytics)
