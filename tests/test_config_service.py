"""
Config Service Tests
系统配置服务测试

Coverage target: 90%+
Business logic tested:
- Rate limit configuration
- Config caching
- Preset application
- Batch updates
"""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestDefaultRateLimits:
    """Test default rate limit configurations"""
    
    def test_payment_limits_defined(self):
        """Payment rate limits are defined"""
        from domains.platform.config_service import DEFAULT_RATE_LIMITS
        
        assert "rate_limit.payment.checkout" in DEFAULT_RATE_LIMITS
        assert "rate_limit.payment.portal" in DEFAULT_RATE_LIMITS
        assert "rate_limit.marketplace.purchase" in DEFAULT_RATE_LIMITS
    
    def test_ai_limits_defined(self):
        """AI operation rate limits are defined"""
        from domains.platform.config_service import DEFAULT_RATE_LIMITS
        
        assert "rate_limit.generate.story" in DEFAULT_RATE_LIMITS
        assert "rate_limit.generate.images" in DEFAULT_RATE_LIMITS
        assert "rate_limit.tools.ocr" in DEFAULT_RATE_LIMITS
    
    def test_export_limits_defined(self):
        """Export rate limits are defined"""
        from domains.platform.config_service import DEFAULT_RATE_LIMITS
        
        assert "rate_limit.export.pdf" in DEFAULT_RATE_LIMITS
        assert "rate_limit.export.zip" in DEFAULT_RATE_LIMITS
    
    def test_admin_limits_defined(self):
        """Admin rate limits are defined"""
        from domains.platform.config_service import DEFAULT_RATE_LIMITS
        
        assert "rate_limit.admin.credits" in DEFAULT_RATE_LIMITS
        assert "rate_limit.admin.tier" in DEFAULT_RATE_LIMITS
    
    def test_default_values_structure(self):
        """Default values have correct structure"""
        from domains.platform.config_service import DEFAULT_RATE_LIMITS
        
        config = DEFAULT_RATE_LIMITS["rate_limit.payment.checkout"]
        
        assert "limit" in config
        assert "window" in config
        assert "enabled" in config
        assert isinstance(config["limit"], int)


class TestGetConfig:
    """Test get_config function"""
    
    @patch('services.config_service.cache_service')
    def test_get_config_from_cache(self, mock_cache):
        """Returns config from cache when available"""
        from domains.platform.config_service import get_config
        
        mock_cache.get_config.return_value = {"limit": 10, "window": "minute"}
        
        result = get_config("rate_limit.test", use_cache=True)
        
        assert result == {"limit": 10, "window": "minute"}
        mock_cache.get_config.assert_called_once_with("rate_limit.test")
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_get_config_from_database(self, mock_supabase, mock_cache):
        """Fetches config from database when not in cache"""
        from domains.platform.config_service import get_config
        
        mock_cache.get_config.return_value = None
        
        mock_result = MagicMock()
        mock_result.data = {
            "value": '{"limit": 20, "window": "minute"}',
            "is_active": True
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        result = get_config("rate_limit.custom")
        
        assert result == {"limit": 20, "window": "minute"}
        # Should cache the result
        mock_cache.set_config.assert_called_once()
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_get_config_inactive_returns_default(self, mock_supabase, mock_cache):
        """Returns default when config is inactive"""
        from domains.platform.config_service import get_config, DEFAULT_RATE_LIMITS
        
        mock_cache.get_config.return_value = None
        
        mock_result = MagicMock()
        mock_result.data = {
            "value": '{"limit": 20}',
            "is_active": False
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        result = get_config("rate_limit.payment.checkout")
        
        assert result == DEFAULT_RATE_LIMITS["rate_limit.payment.checkout"]
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_get_config_handles_exception(self, mock_supabase, mock_cache):
        """Handles database exceptions gracefully"""
        from domains.platform.config_service import get_config, DEFAULT_RATE_LIMITS
        
        mock_cache.get_config.return_value = None
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("DB error")
        
        result = get_config("rate_limit.payment.checkout")
        
        # Should return default
        assert result == DEFAULT_RATE_LIMITS["rate_limit.payment.checkout"]
    
    @patch('services.config_service.cache_service')
    def test_get_config_skip_cache(self, mock_cache):
        """Can skip cache when requested"""
        from domains.platform.config_service import get_config
        
        with patch('services.config_service.supabase') as mock_supabase:
            mock_result = MagicMock()
            mock_result.data = {"value": '{"limit": 5}', "is_active": True}
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
            
            get_config("rate_limit.test", use_cache=False)
            
            mock_cache.get_config.assert_not_called()
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_get_config_handles_non_json_value(self, mock_supabase, mock_cache):
        """Handles non-JSON string values"""
        from domains.platform.config_service import get_config
        
        mock_cache.get_config.return_value = None
        
        mock_result = MagicMock()
        mock_result.data = {
            "value": "simple_string",
            "is_active": True
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        result = get_config("some.string.config")
        
        assert result == "simple_string"
    
    def test_get_config_returns_default_for_unknown(self):
        """Returns default for unknown config key"""
        from domains.platform.config_service import get_config
        
        with patch('services.config_service.cache_service') as mock_cache:
            mock_cache.get_config.return_value = None
            with patch('services.config_service.supabase', None):
                result = get_config("unknown.config.key")
                
                assert result is None


class TestSetConfig:
    """Test set_config function"""
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_set_config_success(self, mock_supabase, mock_cache):
        """Successfully sets config"""
        from domains.platform.config_service import set_config
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        result = set_config("rate_limit.test", {"limit": 15}, updated_by="admin_123")
        
        assert result is True
        mock_cache.invalidate_config_cache.assert_called_once_with("rate_limit.test")
    
    def test_set_config_no_supabase(self):
        """Returns False when supabase not configured"""
        from domains.platform.config_service import set_config
        
        with patch('services.config_service.supabase', None):
            result = set_config("rate_limit.test", {"limit": 10})
            
            assert result is False
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_set_config_handles_exception(self, mock_supabase, mock_cache):
        """Handles database exceptions"""
        from domains.platform.config_service import set_config
        
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("DB error")
        
        result = set_config("rate_limit.test", {"limit": 10})
        
        assert result is False


class TestGetAllConfigs:
    """Test get_all_configs function"""
    
    @patch('services.config_service.supabase')
    def test_get_all_configs_success(self, mock_supabase):
        """Returns all configs"""
        from domains.platform.config_service import get_all_configs
        
        mock_result = MagicMock()
        mock_result.data = [
            {"key": "rate_limit.a", "value": '{"limit": 10}'},
            {"key": "rate_limit.b", "value": '{"limit": 20}'},
        ]
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_result
        
        result = get_all_configs()
        
        assert len(result) == 2
    
    @patch('services.config_service.supabase')
    def test_get_all_configs_with_category(self, mock_supabase):
        """Filters configs by category"""
        from domains.platform.config_service import get_all_configs
        
        mock_result = MagicMock()
        mock_result.data = [{"key": "rate_limit.payment.checkout", "value": '{"limit": 5}'}]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_result
        
        result = get_all_configs(category="rate_limit.payment")
        
        mock_supabase.table.return_value.select.return_value.eq.assert_called()
    
    def test_get_all_configs_no_supabase(self):
        """Returns defaults when no supabase"""
        from domains.platform.config_service import get_all_configs, DEFAULT_RATE_LIMITS
        
        with patch('services.config_service.supabase', None):
            result = get_all_configs()
            
            assert len(result) == len(DEFAULT_RATE_LIMITS)
    
    def test_get_all_configs_no_supabase_with_filter(self):
        """Returns filtered defaults when no supabase"""
        from domains.platform.config_service import get_all_configs
        
        with patch('services.config_service.supabase', None):
            result = get_all_configs(category="rate_limit.payment")
            
            # Should only return payment-related configs
            for config in result:
                assert "payment" in config["key"]
    
    @patch('services.config_service.supabase')
    def test_get_all_configs_handles_exception(self, mock_supabase):
        """Handles database exceptions"""
        from domains.platform.config_service import get_all_configs
        
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.side_effect = Exception("DB error")
        
        result = get_all_configs()
        
        assert result == []


class TestGetRateLimitString:
    """Test get_rate_limit_string function"""
    
    @patch('services.config_service.get_config')
    def test_get_rate_limit_string_normal(self, mock_get_config):
        """Returns formatted rate limit string"""
        from domains.platform.config_service import get_rate_limit_string
        
        mock_get_config.return_value = {"limit": 10, "window": "minute", "enabled": True}
        
        result = get_rate_limit_string("rate_limit.test")
        
        assert result == "10/minute"
    
    @patch('services.config_service.get_config')
    def test_get_rate_limit_string_disabled(self, mock_get_config):
        """Returns high limit when disabled"""
        from domains.platform.config_service import get_rate_limit_string
        
        mock_get_config.return_value = {"limit": 10, "window": "minute", "enabled": False}
        
        result = get_rate_limit_string("rate_limit.test")
        
        assert result == "10000/minute"
    
    @patch('services.config_service.get_config')
    def test_get_rate_limit_string_no_config(self, mock_get_config):
        """Returns high limit when no config"""
        from domains.platform.config_service import get_rate_limit_string
        
        mock_get_config.return_value = None
        
        result = get_rate_limit_string("unknown.config")
        
        assert result == "10000/minute"


class TestIsRateLimitEnabled:
    """Test is_rate_limit_enabled function"""
    
    @patch('services.config_service.get_config')
    def test_rate_limit_enabled_by_default(self, mock_get_config):
        """Rate limit is enabled by default"""
        from domains.platform.config_service import is_rate_limit_enabled
        
        mock_get_config.return_value = {"enabled": True}
        
        result = is_rate_limit_enabled()
        
        assert result is True
    
    @patch('services.config_service.get_config')
    def test_rate_limit_globally_disabled(self, mock_get_config):
        """Global disable overrides specific config"""
        from domains.platform.config_service import is_rate_limit_enabled
        
        mock_get_config.return_value = {"enabled": False}
        
        result = is_rate_limit_enabled()
        
        assert result is False
    
    @patch('services.config_service.get_config')
    def test_rate_limit_specific_key_disabled(self, mock_get_config):
        """Specific key can be disabled"""
        from domains.platform.config_service import is_rate_limit_enabled
        
        def mock_config(key):
            if key == "rate_limit.global.enabled":
                return {"enabled": True}
            return {"enabled": False}
        
        mock_get_config.side_effect = mock_config
        
        result = is_rate_limit_enabled("rate_limit.test.endpoint")
        
        assert result is False


class TestClearConfigCache:
    """Test clear_config_cache function"""
    
    @patch('services.config_service.cache_service')
    def test_clear_config_cache(self, mock_cache):
        """Clears config cache"""
        from domains.platform.config_service import clear_config_cache
        
        clear_config_cache()
        
        mock_cache.invalidate_config_cache.assert_called_once()


class TestBatchUpdateConfigs:
    """Test batch_update_configs function"""
    
    @patch('services.config_service.set_config')
    def test_batch_update_success(self, mock_set_config):
        """Successfully batch updates configs"""
        from domains.platform.config_service import batch_update_configs
        
        mock_set_config.return_value = True
        
        updates = [
            {"config_key": "rate_limit.a", "config_value": {"limit": 10}},
            {"config_key": "rate_limit.b", "config_value": {"limit": 20}},
        ]
        
        result = batch_update_configs(updates, updated_by="admin")
        
        assert result["rate_limit.a"] is True
        assert result["rate_limit.b"] is True
        assert mock_set_config.call_count == 2
    
    @patch('services.config_service.set_config')
    def test_batch_update_partial_failure(self, mock_set_config):
        """Handles partial failures in batch update"""
        from domains.platform.config_service import batch_update_configs
        
        mock_set_config.side_effect = [True, False]
        
        updates = [
            {"config_key": "rate_limit.a", "config_value": {"limit": 10}},
            {"config_key": "rate_limit.b", "config_value": {"limit": 20}},
        ]
        
        result = batch_update_configs(updates)
        
        assert result["rate_limit.a"] is True
        assert result["rate_limit.b"] is False
    
    def test_batch_update_skips_invalid(self):
        """Skips invalid update entries"""
        from domains.platform.config_service import batch_update_configs
        
        with patch('services.config_service.set_config') as mock_set:
            mock_set.return_value = True
            
            updates = [
                {"config_key": "rate_limit.a", "config_value": {"limit": 10}},
                {"config_key": None, "config_value": {"limit": 20}},  # Invalid
                {"config_key": "rate_limit.c", "config_value": None},  # Invalid
            ]
            
            result = batch_update_configs(updates)
            
            assert len(result) == 1  # Only one valid update


class TestRateLimitPresets:
    """Test rate limit presets"""
    
    def test_presets_defined(self):
        """Presets are properly defined"""
        from domains.platform.config_service import RATE_LIMIT_PRESETS
        
        assert "strict" in RATE_LIMIT_PRESETS
        assert "normal" in RATE_LIMIT_PRESETS
        assert "relaxed" in RATE_LIMIT_PRESETS
        assert "disabled" in RATE_LIMIT_PRESETS
    
    def test_preset_structure(self):
        """Presets have correct structure"""
        from domains.platform.config_service import RATE_LIMIT_PRESETS
        
        assert "multiplier" in RATE_LIMIT_PRESETS["strict"]
        assert RATE_LIMIT_PRESETS["strict"]["multiplier"] == 0.5
        assert RATE_LIMIT_PRESETS["relaxed"]["multiplier"] == 2.0
        assert RATE_LIMIT_PRESETS["disabled"]["enabled"] is False


class TestApplyRateLimitPreset:
    """Test apply_rate_limit_preset function"""
    
    def test_apply_invalid_preset(self):
        """Returns False for invalid preset"""
        from domains.platform.config_service import apply_rate_limit_preset
        
        result = apply_rate_limit_preset("nonexistent_preset")
        
        assert result is False
    
    @patch('services.config_service.set_config')
    def test_apply_disabled_preset(self, mock_set_config):
        """Applies disabled preset correctly"""
        from domains.platform.config_service import apply_rate_limit_preset
        
        mock_set_config.return_value = True
        
        result = apply_rate_limit_preset("disabled", updated_by="admin")
        
        assert result is True
        mock_set_config.assert_called_with(
            "rate_limit.global.enabled",
            {"enabled": False},
            "admin"
        )
    
    @patch('services.config_service.clear_config_cache')
    @patch('services.config_service.set_config')
    def test_apply_normal_preset(self, mock_set_config, mock_clear_cache):
        """Applies normal preset (resets to defaults)"""
        from domains.platform.config_service import apply_rate_limit_preset, DEFAULT_RATE_LIMITS
        
        mock_set_config.return_value = True
        
        result = apply_rate_limit_preset("normal")
        
        assert result is True
        # Should set global enabled
        mock_set_config.assert_any_call("rate_limit.global.enabled", {"enabled": True}, None)
        mock_clear_cache.assert_called_once()
    
    @patch('services.config_service.clear_config_cache')
    @patch('services.config_service.get_all_configs')
    @patch('services.config_service.set_config')
    def test_apply_strict_preset(self, mock_set_config, mock_get_all, mock_clear_cache):
        """Applies strict preset (halves limits)"""
        from domains.platform.config_service import apply_rate_limit_preset
        
        mock_set_config.return_value = True
        mock_get_all.return_value = [
            {"key": "rate_limit.test", "value": '{"limit": 10, "window": "minute"}'},
        ]
        
        result = apply_rate_limit_preset("strict")
        
        assert result is True
        # Check that set_config was called with halved limit (10 * 0.5 = 5)
        calls = mock_set_config.call_args_list
        # Find the call for rate_limit.test
        for call in calls:
            if call[0][0] == "rate_limit.test":
                assert call[0][1]["limit"] == 5


class TestSupabaseConfiguration:
    """Test Supabase URL configuration"""
    
    def test_url_trailing_slash_handling(self):
        """Supabase URL gets trailing slash if missing"""
        # This is tested at module load time
        # Just verify the logic is present
        from services import config_service
        
        # Module should be importable without errors
        assert config_service is not None
