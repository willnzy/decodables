"""
CAPI Service Tests
Conversions API 服务测试

Coverage target: 90%+
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import time


# Helper for running async functions
def run_async(coro):
    """Helper to run async functions in sync tests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestCAPIEventType:
    """Test CAPIEventType enum"""
    
    def test_event_types_exist(self):
        """All event types are defined"""
        from services.capi_service import CAPIEventType
        
        assert CAPIEventType.USER_REGISTERED == "user_registered"
        assert CAPIEventType.USER_LOGGED_IN == "user_logged_in"
        assert CAPIEventType.SUBSCRIPTION_STARTED == "subscription_started"
        assert CAPIEventType.CREDITS_PURCHASED == "credits_purchased"
        assert CAPIEventType.AI_GENERATION_STARTED == "ai_generation_started"
        assert CAPIEventType.PROJECT_CREATED == "project_created"
        assert CAPIEventType.PAGE_VIEWED == "page_viewed"


class TestCAPIUserData:
    """Test CAPIUserData dataclass"""
    
    def test_default_values(self):
        """All fields default to None"""
        from services.capi_service import CAPIUserData
        
        user_data = CAPIUserData()
        assert user_data.email is None
        assert user_data.phone is None
        assert user_data.first_name is None
        assert user_data.external_id is None
        assert user_data.client_ip_address is None
    
    def test_with_all_fields(self):
        """Can set all fields"""
        from services.capi_service import CAPIUserData
        
        user_data = CAPIUserData(
            email="hashed_email",
            phone="hashed_phone",
            first_name="hashed_first",
            last_name="hashed_last",
            external_id="hashed_id",
            client_ip_address="1.2.3.4",
            client_user_agent="Mozilla/5.0",
            fbc="fb_click_id",
            fbp="fb_browser_id",
        )
        
        assert user_data.email == "hashed_email"
        assert user_data.client_ip_address == "1.2.3.4"
        assert user_data.fbc == "fb_click_id"


class TestCAPIEvent:
    """Test CAPIEvent dataclass"""
    
    def test_required_fields(self):
        """Required fields must be provided"""
        from services.capi_service import CAPIEvent, CAPIEventType
        
        event = CAPIEvent(
            event_name=CAPIEventType.USER_REGISTERED,
            event_id="event-123",
            event_time=1704067200,
        )
        
        assert event.event_name == CAPIEventType.USER_REGISTERED
        assert event.event_id == "event-123"
        assert event.event_time == 1704067200
        assert event.action_source == "website"
    
    def test_optional_fields(self):
        """Optional fields have defaults"""
        from services.capi_service import CAPIEvent, CAPIEventType
        
        event = CAPIEvent(
            event_name=CAPIEventType.CREDITS_PURCHASED,
            event_id="event-456",
            event_time=1704067200,
        )
        
        assert event.event_source_url is None
        assert event.user_data is None
        assert event.custom_data is None


class TestHashingFunctions:
    """Test hashing utility functions"""
    
    def test_sha256_hash_basic(self):
        """SHA256 hash works correctly"""
        from services.capi_service import sha256_hash
        
        result = sha256_hash("test@example.com")
        
        # Should be 64 character hex string
        assert len(result) == 64
        assert all(c in '0123456789abcdef' for c in result)
    
    def test_sha256_hash_lowercase(self):
        """SHA256 hash normalizes to lowercase"""
        from services.capi_service import sha256_hash
        
        result1 = sha256_hash("TEST@EXAMPLE.COM")
        result2 = sha256_hash("test@example.com")
        
        assert result1 == result2
    
    def test_sha256_hash_strips_whitespace(self):
        """SHA256 hash strips whitespace"""
        from services.capi_service import sha256_hash
        
        result1 = sha256_hash("  test@example.com  ")
        result2 = sha256_hash("test@example.com")
        
        assert result1 == result2
    
    def test_sha256_hash_empty_returns_none(self):
        """SHA256 hash returns None for empty input"""
        from services.capi_service import sha256_hash
        
        assert sha256_hash("") is None
        assert sha256_hash(None) is None
    
    def test_hash_email(self):
        """hash_email function works"""
        from services.capi_service import hash_email
        
        result = hash_email("user@example.com")
        assert len(result) == 64
    
    def test_hash_email_none(self):
        """hash_email returns None for empty"""
        from services.capi_service import hash_email
        
        assert hash_email(None) is None
        assert hash_email("") is None
    
    def test_hash_phone(self):
        """hash_phone function works"""
        from services.capi_service import hash_phone
        
        result = hash_phone("+14155551234")
        assert len(result) == 64
    
    def test_hash_phone_cleans_input(self):
        """hash_phone removes non-numeric characters"""
        from services.capi_service import hash_phone
        
        result1 = hash_phone("+1 (415) 555-1234")
        result2 = hash_phone("+14155551234")
        
        assert result1 == result2
    
    def test_hash_phone_none(self):
        """hash_phone returns None for empty"""
        from services.capi_service import hash_phone
        
        assert hash_phone(None) is None
        assert hash_phone("") is None


class TestFacebookCAPIProvider:
    """Test FacebookCAPIProvider"""
    
    def test_not_configured_without_env(self):
        """Not configured without environment variables"""
        from services.capi_service import FacebookCAPIProvider
        
        with patch.dict('os.environ', {}, clear=True):
            provider = FacebookCAPIProvider()
            assert provider.is_configured() is False
    
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    def test_configured_with_env(self):
        """Configured with environment variables"""
        from services.capi_service import FacebookCAPIProvider
        
        provider = FacebookCAPIProvider()
        assert provider.is_configured() is True
    
    @pytest.mark.asyncio
    async def test_send_event_returns_false_when_not_configured(self):
        """Returns False when not configured"""
        from services.capi_service import FacebookCAPIProvider, CAPIEvent, CAPIEventType
        
        with patch.dict('os.environ', {}, clear=True):
            provider = FacebookCAPIProvider()
            event = CAPIEvent(
                event_name=CAPIEventType.USER_REGISTERED,
                event_id="test-123",
                event_time=int(time.time()),
            )
            
            result = await provider.send_event(event)
            assert result is False
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    async def test_send_event_success(self):
        """Successfully sends event (stub)"""
        from services.capi_service import FacebookCAPIProvider, CAPIEvent, CAPIEventType
        
        provider = FacebookCAPIProvider()
        event = CAPIEvent(
            event_name=CAPIEventType.USER_REGISTERED,
            event_id="test-123",
            event_time=int(time.time()),
        )
        
        result = await provider.send_event(event)
        assert result is True
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    async def test_send_event_unknown_type(self):
        """Returns False for unknown event type"""
        from services.capi_service import FacebookCAPIProvider, CAPIEvent
        
        provider = FacebookCAPIProvider()
        event = CAPIEvent(
            event_name="unknown_event",  # Not in EVENT_MAP
            event_id="test-123",
            event_time=int(time.time()),
        )
        
        result = await provider.send_event(event)
        assert result is False
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123', 'FB_TEST_EVENT_CODE': 'TEST123'})
    async def test_send_event_with_test_code(self):
        """Includes test event code when configured"""
        from services.capi_service import FacebookCAPIProvider, CAPIEvent, CAPIEventType
        
        provider = FacebookCAPIProvider()
        assert provider.test_event_code == "TEST123"
        
        event = CAPIEvent(
            event_name=CAPIEventType.CREDITS_PURCHASED,
            event_id="test-123",
            event_time=int(time.time()),
        )
        
        result = await provider.send_event(event)
        assert result is True
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    async def test_send_events_batch(self):
        """Batch sends events one by one"""
        from services.capi_service import FacebookCAPIProvider, CAPIEvent, CAPIEventType
        
        provider = FacebookCAPIProvider()
        events = [
            CAPIEvent(event_name=CAPIEventType.USER_REGISTERED, event_id="1", event_time=int(time.time())),
            CAPIEvent(event_name=CAPIEventType.CREDITS_PURCHASED, event_id="2", event_time=int(time.time())),
        ]
        
        result = await provider.send_events_batch(events)
        
        assert result["sent"] == 2
        assert result["failed"] == 0
    
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    def test_build_user_data_with_all_fields(self):
        """Builds user_data with all fields"""
        from services.capi_service import FacebookCAPIProvider, CAPIUserData
        
        provider = FacebookCAPIProvider()
        user_data = CAPIUserData(
            email="hashed_email",
            phone="hashed_phone",
            first_name="hashed_first",
            last_name="hashed_last",
            external_id="hashed_id",
            client_ip_address="1.2.3.4",
            client_user_agent="Mozilla/5.0",
            fbc="fb_click_id",
            fbp="fb_browser_id",
        )
        
        result = provider._build_user_data(user_data)
        
        assert result["em"] == ["hashed_email"]
        assert result["ph"] == ["hashed_phone"]
        assert result["fn"] == ["hashed_first"]
        assert result["ln"] == ["hashed_last"]
        assert result["external_id"] == ["hashed_id"]
        assert result["client_ip_address"] == "1.2.3.4"
        assert result["client_user_agent"] == "Mozilla/5.0"
        assert result["fbc"] == "fb_click_id"
        assert result["fbp"] == "fb_browser_id"
    
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    def test_build_user_data_empty(self):
        """Returns empty dict for None user_data"""
        from services.capi_service import FacebookCAPIProvider
        
        provider = FacebookCAPIProvider()
        result = provider._build_user_data(None)
        
        assert result == {}


class TestTikTokEventsAPIProvider:
    """Test TikTokEventsAPIProvider"""
    
    def test_not_configured_without_env(self):
        """Not configured without environment variables"""
        from services.capi_service import TikTokEventsAPIProvider
        
        with patch.dict('os.environ', {}, clear=True):
            provider = TikTokEventsAPIProvider()
            assert provider.is_configured() is False
    
    @patch.dict('os.environ', {'TIKTOK_PIXEL_ID': 'pixel123', 'TIKTOK_ACCESS_TOKEN': 'token123'})
    def test_configured_with_env(self):
        """Configured with environment variables"""
        from services.capi_service import TikTokEventsAPIProvider
        
        provider = TikTokEventsAPIProvider()
        assert provider.is_configured() is True
    
    @pytest.mark.asyncio
    async def test_send_event_returns_false_when_not_configured(self):
        """Returns False when not configured"""
        from services.capi_service import TikTokEventsAPIProvider, CAPIEvent, CAPIEventType
        
        with patch.dict('os.environ', {}, clear=True):
            provider = TikTokEventsAPIProvider()
            event = CAPIEvent(
                event_name=CAPIEventType.USER_REGISTERED,
                event_id="test-123",
                event_time=int(time.time()),
            )
            
            result = await provider.send_event(event)
            assert result is False
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TIKTOK_PIXEL_ID': 'pixel123', 'TIKTOK_ACCESS_TOKEN': 'token123'})
    async def test_send_event_success(self):
        """Successfully sends event (stub)"""
        from services.capi_service import TikTokEventsAPIProvider, CAPIEvent, CAPIEventType
        
        provider = TikTokEventsAPIProvider()
        event = CAPIEvent(
            event_name=CAPIEventType.CREDITS_PURCHASED,
            event_id="test-123",
            event_time=int(time.time()),
        )
        
        result = await provider.send_event(event)
        assert result is True
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TIKTOK_PIXEL_ID': 'pixel123', 'TIKTOK_ACCESS_TOKEN': 'token123'})
    async def test_send_event_unknown_type(self):
        """Returns False for unknown event type"""
        from services.capi_service import TikTokEventsAPIProvider, CAPIEvent
        
        provider = TikTokEventsAPIProvider()
        event = CAPIEvent(
            event_name="unknown_event",
            event_id="test-123",
            event_time=int(time.time()),
        )
        
        result = await provider.send_event(event)
        assert result is False
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TIKTOK_PIXEL_ID': 'pixel123', 'TIKTOK_ACCESS_TOKEN': 'token123'})
    async def test_send_events_batch(self):
        """Batch sends events"""
        from services.capi_service import TikTokEventsAPIProvider, CAPIEvent, CAPIEventType
        
        provider = TikTokEventsAPIProvider()
        events = [
            CAPIEvent(event_name=CAPIEventType.USER_REGISTERED, event_id="1", event_time=int(time.time())),
        ]
        
        result = await provider.send_events_batch(events)
        
        assert result["sent"] == 1


class TestServerSideGTMProvider:
    """Test ServerSideGTMProvider"""
    
    def test_not_configured_without_env(self):
        """Not configured without environment variables"""
        from services.capi_service import ServerSideGTMProvider
        
        with patch.dict('os.environ', {}, clear=True):
            provider = ServerSideGTMProvider()
            assert provider.is_configured() is False
    
    @patch.dict('os.environ', {'SGTM_SERVER_URL': 'https://gtm.example.com'})
    def test_configured_with_env(self):
        """Configured with environment variables"""
        from services.capi_service import ServerSideGTMProvider
        
        provider = ServerSideGTMProvider()
        assert provider.is_configured() is True
    
    @pytest.mark.asyncio
    async def test_send_event_returns_false_when_not_configured(self):
        """Returns False when not configured"""
        from services.capi_service import ServerSideGTMProvider, CAPIEvent, CAPIEventType
        
        with patch.dict('os.environ', {}, clear=True):
            provider = ServerSideGTMProvider()
            event = CAPIEvent(
                event_name=CAPIEventType.PAGE_VIEWED,
                event_id="test-123",
                event_time=int(time.time()),
            )
            
            result = await provider.send_event(event)
            assert result is False
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'SGTM_SERVER_URL': 'https://gtm.example.com'})
    async def test_send_event_success(self):
        """Successfully sends event (stub)"""
        from services.capi_service import ServerSideGTMProvider, CAPIEvent, CAPIEventType
        
        provider = ServerSideGTMProvider()
        event = CAPIEvent(
            event_name=CAPIEventType.PROJECT_CREATED,
            event_id="test-123",
            event_time=int(time.time()),
        )
        
        result = await provider.send_event(event)
        assert result is True
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'SGTM_SERVER_URL': 'https://gtm.example.com'})
    async def test_send_events_batch(self):
        """Batch sends events"""
        from services.capi_service import ServerSideGTMProvider, CAPIEvent, CAPIEventType
        
        provider = ServerSideGTMProvider()
        events = [
            CAPIEvent(event_name=CAPIEventType.PAGE_VIEWED, event_id="1", event_time=int(time.time())),
        ]
        
        result = await provider.send_events_batch(events)
        
        assert result["sent"] == 1


class TestCAPIService:
    """Test CAPIService main class"""
    
    def test_no_providers_when_not_configured(self):
        """No providers when env vars not set"""
        from services.capi_service import CAPIService
        
        with patch.dict('os.environ', {}, clear=True):
            service = CAPIService()
            assert service.is_enabled() is False
            assert len(service.providers) == 0
    
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    def test_facebook_provider_enabled(self):
        """Facebook provider enabled when configured"""
        from services.capi_service import CAPIService
        
        service = CAPIService()
        assert service.is_enabled() is True
        assert len(service.providers) == 1
    
    @patch.dict('os.environ', {
        'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123',
        'TIKTOK_PIXEL_ID': 'ttpixel', 'TIKTOK_ACCESS_TOKEN': 'tttoken',
    })
    def test_multiple_providers_enabled(self):
        """Multiple providers enabled"""
        from services.capi_service import CAPIService
        
        service = CAPIService()
        assert service.is_enabled() is True
        assert len(service.providers) == 2
    
    @pytest.mark.asyncio
    async def test_track_conversion_skipped_when_not_enabled(self):
        """Track conversion skipped when no providers"""
        from services.capi_service import CAPIService, CAPIEventType
        
        with patch.dict('os.environ', {}, clear=True):
            service = CAPIService()
            
            result = await service.track_conversion(
                event_type=CAPIEventType.USER_REGISTERED,
                event_id="test-123",
                event_time=int(time.time()),
            )
            
            assert result["status"] == "skipped"
            assert result["reason"] == "no_providers_configured"
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    async def test_track_conversion_success(self):
        """Track conversion succeeds"""
        from services.capi_service import CAPIService, CAPIEventType, CAPIUserData
        
        service = CAPIService()
        
        result = await service.track_conversion(
            event_type=CAPIEventType.CREDITS_PURCHASED,
            event_id="test-123",
            event_time=int(time.time()),
            user_data=CAPIUserData(email="hashed_email"),
            custom_data={"value": 9.99, "currency": "USD"},
            event_source_url="https://example.com/checkout",
        )
        
        assert "FacebookCAPIProvider" in result
        assert result["FacebookCAPIProvider"] == "success"
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    async def test_track_conversion_handles_exception(self):
        """Track conversion handles provider exception"""
        from services.capi_service import CAPIService, CAPIEventType
        
        service = CAPIService()
        
        # Mock provider to raise exception
        service.providers[0].send_event = AsyncMock(side_effect=Exception("Network error"))
        
        result = await service.track_conversion(
            event_type=CAPIEventType.USER_REGISTERED,
            event_id="test-123",
            event_time=int(time.time()),
        )
        
        assert "error:" in result["FacebookCAPIProvider"]


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    @patch('services.capi_service.capi_service')
    async def test_track_purchase_conversion(self, mock_service):
        """Track purchase conversion"""
        from services.capi_service import track_purchase_conversion
        
        mock_service.track_conversion = AsyncMock(return_value={"status": "success"})
        
        result = await track_purchase_conversion(
            event_id="purchase-123",
            event_time=int(time.time()),
            value=9.99,
            currency="USD",
            user_email="test@example.com",
            user_id="user_123",
            transaction_id="txn_abc",
            event_source_url="https://example.com/checkout",
        )
        
        mock_service.track_conversion.assert_called_once()
        call_kwargs = mock_service.track_conversion.call_args[1]
        assert call_kwargs["custom_data"]["value"] == 9.99
        assert call_kwargs["custom_data"]["transaction_id"] == "txn_abc"
    
    @pytest.mark.asyncio
    @patch('services.capi_service.capi_service')
    async def test_track_purchase_conversion_without_optional(self, mock_service):
        """Track purchase without optional fields"""
        from services.capi_service import track_purchase_conversion
        
        mock_service.track_conversion = AsyncMock(return_value={"status": "success"})
        
        result = await track_purchase_conversion(
            event_id="purchase-123",
            event_time=int(time.time()),
            value=19.99,
            currency="USD",
        )
        
        call_kwargs = mock_service.track_conversion.call_args[1]
        assert "transaction_id" not in call_kwargs["custom_data"]
    
    @pytest.mark.asyncio
    @patch('services.capi_service.capi_service')
    async def test_track_signup_conversion(self, mock_service):
        """Track signup conversion"""
        from services.capi_service import track_signup_conversion
        
        mock_service.track_conversion = AsyncMock(return_value={"status": "success"})
        
        result = await track_signup_conversion(
            event_id="signup-123",
            event_time=int(time.time()),
            user_email="new@example.com",
            user_id="user_new",
            signup_method="google",
            event_source_url="https://example.com/signup",
        )
        
        mock_service.track_conversion.assert_called_once()
        call_kwargs = mock_service.track_conversion.call_args[1]
        assert call_kwargs["custom_data"]["signup_method"] == "google"


class TestSingletonInstance:
    """Test singleton capi_service instance"""
    
    def test_singleton_exists(self):
        """Singleton instance exists"""
        from services.capi_service import capi_service
        assert capi_service is not None
    
    def test_singleton_is_capi_service(self):
        """Singleton is CAPIService instance"""
        from services.capi_service import capi_service, CAPIService
        assert isinstance(capi_service, CAPIService)


class TestMoreEventTypes:
    """Test additional event type mappings"""
    
    def test_all_event_types_defined(self):
        """All CAPIEventType values exist"""
        from services.capi_service import CAPIEventType
        
        # User lifecycle
        assert CAPIEventType.USER_REGISTERED.value == "user_registered"
        assert CAPIEventType.USER_LOGGED_IN.value == "user_logged_in"
        
        # Monetization
        assert CAPIEventType.SUBSCRIPTION_STARTED.value == "subscription_started"
        assert CAPIEventType.SUBSCRIPTION_UPGRADED.value == "subscription_upgraded"
        assert CAPIEventType.CREDITS_PURCHASED.value == "credits_purchased"
        assert CAPIEventType.MARKETPLACE_PURCHASED.value == "marketplace_purchased"
        
        # Engagement
        assert CAPIEventType.AI_GENERATION_STARTED.value == "ai_generation_started"
        assert CAPIEventType.AI_GENERATION_COMPLETED.value == "ai_generation_completed"
        assert CAPIEventType.PROJECT_CREATED.value == "project_created"
        assert CAPIEventType.PROJECT_EXPORTED.value == "project_exported"
        
        # Page views
        assert CAPIEventType.PAGE_VIEWED.value == "page_viewed"


class TestFacebookEventMapping:
    """Test Facebook event type mapping"""
    
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    def test_all_event_types_mapped(self):
        """All CAPIEventTypes are mapped to Facebook events"""
        from services.capi_service import FacebookCAPIProvider, CAPIEventType
        
        provider = FacebookCAPIProvider()
        
        # Verify all event types have mappings
        assert provider.EVENT_MAP[CAPIEventType.USER_REGISTERED] == "CompleteRegistration"
        assert provider.EVENT_MAP[CAPIEventType.USER_LOGGED_IN] == "Login"
        assert provider.EVENT_MAP[CAPIEventType.SUBSCRIPTION_STARTED] == "Subscribe"
        assert provider.EVENT_MAP[CAPIEventType.SUBSCRIPTION_UPGRADED] == "Subscribe"
        assert provider.EVENT_MAP[CAPIEventType.CREDITS_PURCHASED] == "Purchase"
        assert provider.EVENT_MAP[CAPIEventType.MARKETPLACE_PURCHASED] == "Purchase"
        assert provider.EVENT_MAP[CAPIEventType.AI_GENERATION_STARTED] == "InitiateCheckout"
        assert provider.EVENT_MAP[CAPIEventType.AI_GENERATION_COMPLETED] == "ViewContent"
        assert provider.EVENT_MAP[CAPIEventType.PROJECT_CREATED] == "AddToCart"
        assert provider.EVENT_MAP[CAPIEventType.PROJECT_EXPORTED] == "Lead"
        assert provider.EVENT_MAP[CAPIEventType.PAGE_VIEWED] == "PageView"


class TestTikTokEventMapping:
    """Test TikTok event type mapping"""
    
    @patch.dict('os.environ', {'TIKTOK_PIXEL_ID': 'pixel123', 'TIKTOK_ACCESS_TOKEN': 'token123'})
    def test_all_event_types_mapped(self):
        """All CAPIEventTypes are mapped to TikTok events"""
        from services.capi_service import TikTokEventsAPIProvider, CAPIEventType
        
        provider = TikTokEventsAPIProvider()
        
        assert provider.EVENT_MAP[CAPIEventType.USER_REGISTERED] == "CompleteRegistration"
        assert provider.EVENT_MAP[CAPIEventType.SUBSCRIPTION_STARTED] == "Subscribe"
        assert provider.EVENT_MAP[CAPIEventType.CREDITS_PURCHASED] == "CompletePayment"
        assert provider.EVENT_MAP[CAPIEventType.PROJECT_EXPORTED] == "SubmitForm"
    
    @patch.dict('os.environ', {'TIKTOK_PIXEL_ID': 'pixel123', 'TIKTOK_ACCESS_TOKEN': 'token123', 'TIKTOK_TEST_EVENT_CODE': 'TEST456'})
    def test_test_event_code(self):
        """Test event code is loaded from env"""
        from services.capi_service import TikTokEventsAPIProvider
        
        provider = TikTokEventsAPIProvider()
        assert provider.test_event_code == "TEST456"


class TestServerSideGTMExtended:
    """Extended tests for Server-Side GTM"""
    
    @patch.dict('os.environ', {'SGTM_SERVER_URL': 'https://gtm.example.com', 'SGTM_API_SECRET': 'secret123'})
    def test_api_secret_loaded(self):
        """API secret is loaded from env"""
        from services.capi_service import ServerSideGTMProvider
        
        provider = ServerSideGTMProvider()
        assert provider.api_secret == "secret123"


class TestBatchEventProcessing:
    """Test batch event processing scenarios"""
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'FB_PIXEL_ID': 'pixel123', 'FB_ACCESS_TOKEN': 'token123'})
    async def test_batch_with_mixed_event_types(self):
        """Batch processes events with mixed success/failure"""
        from services.capi_service import FacebookCAPIProvider, CAPIEvent, CAPIEventType
        
        provider = FacebookCAPIProvider()
        events = [
            CAPIEvent(event_name=CAPIEventType.USER_REGISTERED, event_id="1", event_time=int(time.time())),
            CAPIEvent(event_name="unknown_event", event_id="2", event_time=int(time.time())),  # Will fail
            CAPIEvent(event_name=CAPIEventType.PAGE_VIEWED, event_id="3", event_time=int(time.time())),
        ]
        
        result = await provider.send_events_batch(events)
        
        assert result["sent"] == 2
        assert result["failed"] == 1


class TestCAPIServiceProviderInit:
    """Test CAPIService provider initialization"""
    
    @patch.dict('os.environ', {
        'FB_PIXEL_ID': 'fb_pixel', 'FB_ACCESS_TOKEN': 'fb_token',
        'TIKTOK_PIXEL_ID': 'tt_pixel', 'TIKTOK_ACCESS_TOKEN': 'tt_token',
        'SGTM_SERVER_URL': 'https://gtm.example.com',
    })
    def test_all_providers_enabled(self):
        """All three providers enabled"""
        from services.capi_service import CAPIService, FacebookCAPIProvider, TikTokEventsAPIProvider, ServerSideGTMProvider
        
        service = CAPIService()
        
        assert service.is_enabled() is True
        assert len(service.providers) == 3
        
        # Verify each provider type
        provider_types = [type(p).__name__ for p in service.providers]
        assert "FacebookCAPIProvider" in provider_types
        assert "TikTokEventsAPIProvider" in provider_types
        assert "ServerSideGTMProvider" in provider_types


class TestCAPIUserDataEdgeCases:
    """Test CAPIUserData edge cases"""
    
    def test_partial_user_data(self):
        """User data with only some fields"""
        from services.capi_service import CAPIUserData
        
        user_data = CAPIUserData(
            email="hashed_email",
            external_id="hashed_id",
        )
        
        assert user_data.email == "hashed_email"
        assert user_data.phone is None
        assert user_data.external_id == "hashed_id"
        assert user_data.first_name is None


class TestCAPIEventCustomData:
    """Test CAPIEvent custom_data handling"""
    
    def test_event_with_custom_data(self):
        """Event with custom data payload"""
        from services.capi_service import CAPIEvent, CAPIEventType
        
        event = CAPIEvent(
            event_name=CAPIEventType.CREDITS_PURCHASED,
            event_id="evt-123",
            event_time=1704067200,
            custom_data={
                "value": 9.99,
                "currency": "USD",
                "contents": [{"id": "credits_pack_1", "quantity": 1}]
            }
        )
        
        assert event.custom_data["value"] == 9.99
        assert event.custom_data["currency"] == "USD"
    
    def test_event_with_source_url(self):
        """Event with source URL"""
        from services.capi_service import CAPIEvent, CAPIEventType
        
        event = CAPIEvent(
            event_name=CAPIEventType.PAGE_VIEWED,
            event_id="evt-456",
            event_time=1704067200,
            event_source_url="https://example.com/pricing",
            action_source="website",
        )
        
        assert event.event_source_url == "https://example.com/pricing"
        assert event.action_source == "website"
