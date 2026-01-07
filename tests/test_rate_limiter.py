"""
Rate Limiter Service Tests
速率限制器测试

Coverage target: 90%+
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio


class TestCreateLimiterFromUrl:
    """Test create_limiter_from_url function"""
    
    @patch('services.rate_limiter.Limiter')
    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379/0'})
    def test_creates_limiter_with_redis_url_from_env(self, mock_limiter):
        """Uses Redis URL from environment"""
        from infrastructure.rate_limiter import create_limiter_from_url
        
        create_limiter_from_url()
        
        mock_limiter.assert_called_once()
        call_kwargs = mock_limiter.call_args[1]
        assert call_kwargs['storage_uri'] == 'redis://localhost:6379/0'
    
    @patch('services.rate_limiter.Limiter')
    def test_creates_limiter_with_explicit_url(self, mock_limiter):
        """Uses explicit Redis URL parameter"""
        from infrastructure.rate_limiter import create_limiter_from_url
        
        create_limiter_from_url('redis://custom:6379/1')
        
        mock_limiter.assert_called_once()
        call_kwargs = mock_limiter.call_args[1]
        assert call_kwargs['storage_uri'] == 'redis://custom:6379/1'
    
    @patch('services.rate_limiter.Limiter')
    @patch.dict('os.environ', {}, clear=True)
    def test_creates_limiter_without_redis(self, mock_limiter):
        """Falls back to memory when no Redis URL"""
        from infrastructure.rate_limiter import create_limiter_from_url
        
        # Remove REDIS_URL if present
        import os
        os.environ.pop('REDIS_URL', None)
        
        create_limiter_from_url(None)
        
        mock_limiter.assert_called_once()
        # Should not have storage_uri
        call_kwargs = mock_limiter.call_args[1]
        assert 'storage_uri' not in call_kwargs or call_kwargs.get('storage_uri') is None


class TestDynamicLimit:
    """Test dynamic_limit decorator"""
    
    @patch('services.rate_limiter.is_rate_limit_enabled')
    @patch('services.rate_limiter.get_rate_limit_string')
    @patch('services.rate_limiter.limiter')
    def test_async_function_rate_limited(self, mock_limiter, mock_get_string, mock_enabled):
        """Applies rate limit to async function"""
        from infrastructure.rate_limiter import dynamic_limit
        
        mock_enabled.return_value = True
        mock_get_string.return_value = "5/minute"
        
        # Create mock limited function
        mock_limited_func = AsyncMock(return_value="success")
        mock_limiter.limit.return_value = lambda f: mock_limited_func
        
        @dynamic_limit("rate_limit.test")
        async def test_endpoint(request):
            return "original"
        
        # Create mock request
        mock_request = MagicMock()
        
        # Run async function
        result = asyncio.get_event_loop().run_until_complete(test_endpoint(mock_request))
        
        mock_enabled.assert_called_with("rate_limit.test")
        mock_get_string.assert_called_with("rate_limit.test")
    
    @patch('services.rate_limiter.is_rate_limit_enabled')
    def test_async_function_bypasses_when_disabled(self, mock_enabled):
        """Bypasses rate limit when disabled"""
        from infrastructure.rate_limiter import dynamic_limit
        
        mock_enabled.return_value = False
        
        @dynamic_limit("rate_limit.test")
        async def test_endpoint(request):
            return "success"
        
        mock_request = MagicMock()
        result = asyncio.get_event_loop().run_until_complete(test_endpoint(mock_request))
        
        assert result == "success"
        mock_enabled.assert_called_with("rate_limit.test")
    
    @patch('services.rate_limiter.is_rate_limit_enabled')
    def test_sync_function_bypasses_when_disabled(self, mock_enabled):
        """Bypasses rate limit for sync function when disabled"""
        from infrastructure.rate_limiter import dynamic_limit
        
        mock_enabled.return_value = False
        
        @dynamic_limit("rate_limit.test")
        def test_endpoint(request):
            return "sync_success"
        
        mock_request = MagicMock()
        result = test_endpoint(mock_request)
        
        assert result == "sync_success"
    
    @patch('services.rate_limiter.is_rate_limit_enabled')
    @patch('services.rate_limiter.get_rate_limit_string')
    @patch('services.rate_limiter.limiter')
    def test_sync_function_rate_limited(self, mock_limiter, mock_get_string, mock_enabled):
        """Applies rate limit to sync function"""
        from infrastructure.rate_limiter import dynamic_limit
        
        mock_enabled.return_value = True
        mock_get_string.return_value = "10/minute"
        
        mock_limited_func = MagicMock(return_value="limited_result")
        mock_limiter.limit.return_value = lambda f: mock_limited_func
        
        @dynamic_limit("rate_limit.sync_test")
        def test_endpoint(request):
            return "original"
        
        mock_request = MagicMock()
        result = test_endpoint(mock_request)
        
        mock_enabled.assert_called_with("rate_limit.sync_test")
        mock_get_string.assert_called_with("rate_limit.sync_test")
    
    @patch('services.rate_limiter.is_rate_limit_enabled')
    @patch('services.rate_limiter.get_rate_limit_string')
    @patch('services.rate_limiter.limiter')
    @pytest.mark.asyncio
    async def test_raises_429_on_rate_limit_exceeded_async(self, mock_limiter, mock_get_string, mock_enabled):
        """Raises 429 HTTPException when rate limit exceeded (async)"""
        from infrastructure.rate_limiter import dynamic_limit
        from fastapi import HTTPException
        
        mock_enabled.return_value = True
        mock_get_string.return_value = "1/minute"
        
        # Create exception class with RateLimitExceeded in name
        class RateLimitExceeded(Exception):
            pass
        
        mock_limited_func = AsyncMock(side_effect=RateLimitExceeded("too many requests"))
        mock_limiter.limit.return_value = lambda f: mock_limited_func
        
        @dynamic_limit("rate_limit.test")
        async def test_endpoint(request):
            return "success"
        
        mock_request = MagicMock()
        
        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint(mock_request)
        
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail
    
    @patch('services.rate_limiter.is_rate_limit_enabled')
    @patch('services.rate_limiter.get_rate_limit_string')
    @patch('services.rate_limiter.limiter')
    def test_raises_429_on_rate_limit_exceeded_sync(self, mock_limiter, mock_get_string, mock_enabled):
        """Raises 429 HTTPException when rate limit exceeded (sync)"""
        from infrastructure.rate_limiter import dynamic_limit
        from fastapi import HTTPException
        
        mock_enabled.return_value = True
        mock_get_string.return_value = "1/minute"
        
        class RateLimitExceeded(Exception):
            pass
        
        mock_limited_func = MagicMock(side_effect=RateLimitExceeded("too many requests"))
        mock_limiter.limit.return_value = lambda f: mock_limited_func
        
        @dynamic_limit("rate_limit.test")
        def test_endpoint(request):
            return "success"
        
        mock_request = MagicMock()
        
        with pytest.raises(HTTPException) as exc_info:
            test_endpoint(mock_request)
        
        assert exc_info.value.status_code == 429
    
    @patch('services.rate_limiter.is_rate_limit_enabled')
    @patch('services.rate_limiter.get_rate_limit_string')
    @patch('services.rate_limiter.limiter')
    @pytest.mark.asyncio
    async def test_reraises_other_exceptions_async(self, mock_limiter, mock_get_string, mock_enabled):
        """Re-raises non-rate-limit exceptions (async)"""
        from infrastructure.rate_limiter import dynamic_limit
        
        mock_enabled.return_value = True
        mock_get_string.return_value = "5/minute"
        
        mock_limited_func = AsyncMock(side_effect=ValueError("some error"))
        mock_limiter.limit.return_value = lambda f: mock_limited_func
        
        @dynamic_limit("rate_limit.test")
        async def test_endpoint(request):
            return "success"
        
        mock_request = MagicMock()
        
        with pytest.raises(ValueError) as exc_info:
            await test_endpoint(mock_request)
        
        assert "some error" in str(exc_info.value)
    
    @patch('services.rate_limiter.is_rate_limit_enabled')
    @patch('services.rate_limiter.get_rate_limit_string')
    @patch('services.rate_limiter.limiter')
    def test_reraises_other_exceptions_sync(self, mock_limiter, mock_get_string, mock_enabled):
        """Re-raises non-rate-limit exceptions (sync)"""
        from infrastructure.rate_limiter import dynamic_limit
        
        mock_enabled.return_value = True
        mock_get_string.return_value = "5/minute"
        
        mock_limited_func = MagicMock(side_effect=TypeError("type error"))
        mock_limiter.limit.return_value = lambda f: mock_limited_func
        
        @dynamic_limit("rate_limit.test")
        def test_endpoint(request):
            return "success"
        
        mock_request = MagicMock()
        
        with pytest.raises(TypeError):
            test_endpoint(mock_request)


class TestGetCurrentLimits:
    """Test get_current_limits function"""
    
    @patch('services.rate_limiter.is_redis_available')
    @patch('services.config_service.get_all_configs')
    def test_returns_limits_with_redis(self, mock_get_configs, mock_redis_avail):
        """Returns limits with Redis storage indicator"""
        from infrastructure.rate_limiter import get_current_limits
        
        mock_redis_avail.return_value = True
        mock_get_configs.return_value = [
            {"key": "rate_limit.payment.checkout", "value": {"limit": 5, "window": "minute", "enabled": True}},
            {"key": "rate_limit.global.enabled", "value": {"enabled": True}},
        ]
        
        result = get_current_limits()
        
        assert result["storage"] == "redis"
        assert result["global_enabled"] == True
        assert "rate_limit.payment.checkout" in result["limits"]
    
    @patch('services.rate_limiter.is_redis_available')
    @patch('services.config_service.get_all_configs')
    def test_returns_limits_with_memory(self, mock_get_configs, mock_redis_avail):
        """Returns limits with memory storage indicator"""
        from infrastructure.rate_limiter import get_current_limits
        
        mock_redis_avail.return_value = False
        mock_get_configs.return_value = [
            {"key": "rate_limit.api.general", "value": {"limit": 100, "window": "minute", "enabled": True}},
        ]
        
        result = get_current_limits()
        
        assert result["storage"] == "memory"
    
    @patch('services.rate_limiter.is_redis_available')
    @patch('services.config_service.get_all_configs')
    def test_returns_defaults_when_no_configs(self, mock_get_configs, mock_redis_avail):
        """Returns default limits when no configs found"""
        from infrastructure.rate_limiter import get_current_limits
        
        mock_redis_avail.return_value = False
        mock_get_configs.return_value = []
        
        result = get_current_limits()
        
        assert result["global_enabled"] == True
        assert isinstance(result["limits"], dict)
    
    @patch('services.rate_limiter.is_redis_available')
    @patch('services.config_service.get_all_configs')
    def test_handles_json_string_values(self, mock_get_configs, mock_redis_avail):
        """Parses JSON string values correctly"""
        from infrastructure.rate_limiter import get_current_limits
        
        mock_redis_avail.return_value = True
        mock_get_configs.return_value = [
            {"key": "rate_limit.test", "value": '{"limit": 10, "window": "minute"}'},
        ]
        
        result = get_current_limits()
        
        assert result["limits"]["rate_limit.test"]["limit"] == 10
    
    @patch('services.rate_limiter.is_redis_available')
    @patch('services.config_service.get_all_configs')
    def test_handles_invalid_json(self, mock_get_configs, mock_redis_avail):
        """Handles invalid JSON gracefully"""
        from infrastructure.rate_limiter import get_current_limits
        
        mock_redis_avail.return_value = True
        mock_get_configs.return_value = [
            {"key": "rate_limit.invalid", "value": "not-valid-json{"},
        ]
        
        result = get_current_limits()
        
        # Should not raise, just use raw value
        assert "rate_limit.invalid" in result["limits"]
    
    @patch('services.rate_limiter.is_redis_available')
    @patch('services.config_service.get_all_configs')
    def test_global_enabled_false(self, mock_get_configs, mock_redis_avail):
        """Detects global rate limiting disabled"""
        from infrastructure.rate_limiter import get_current_limits
        
        mock_redis_avail.return_value = True
        mock_get_configs.return_value = [
            {"key": "rate_limit.global.enabled", "value": {"enabled": False}},
        ]
        
        result = get_current_limits()
        
        assert result["global_enabled"] == False
    
    @patch('services.rate_limiter.is_redis_available')
    @patch('services.config_service.get_all_configs')
    def test_global_enabled_non_dict_value(self, mock_get_configs, mock_redis_avail):
        """Handles non-dict global enabled value"""
        from infrastructure.rate_limiter import get_current_limits
        
        mock_redis_avail.return_value = True
        mock_get_configs.return_value = [
            {"key": "rate_limit.global.enabled", "value": True},  # Not a dict
        ]
        
        result = get_current_limits()
        
        # Should default to True
        assert result["global_enabled"] == True


class TestLimiterInstance:
    """Test global limiter instance"""
    
    def test_limiter_exists(self):
        """Global limiter instance exists"""
        from infrastructure.rate_limiter import limiter
        assert limiter is not None
    
    def test_limiter_has_limit_method(self):
        """Limiter has limit method"""
        from infrastructure.rate_limiter import limiter
        assert hasattr(limiter, 'limit')
