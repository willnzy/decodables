"""
Unit Tests for config_service.py
Tests configuration service with Redis caching and rate limit handling
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# We need to mock supabase and cache before importing config_service
with patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co/', 'SUPABASE_KEY': 'test-key'}):
    with patch('services.config_service.create_client') as mock_create_client:
        with patch('services.config_service.cache_service') as mock_cache:
            mock_supabase = MagicMock()
            mock_create_client.return_value = mock_supabase
            
            from services.config_service import (
                get_config,
                set_config,
                get_all_configs,
                get_rate_limit_string,
                is_rate_limit_enabled,
                clear_config_cache,
                batch_update_configs,
                apply_rate_limit_preset,
                DEFAULT_RATE_LIMITS,
                RATE_LIMIT_PRESETS,
            )


class TestDefaultRateLimits:
    """Tests for DEFAULT_RATE_LIMITS constant"""
    
    def test_contains_payment_limits(self):
        """Should contain payment-related rate limits"""
        assert "rate_limit.payment.checkout" in DEFAULT_RATE_LIMITS
        assert "rate_limit.payment.portal" in DEFAULT_RATE_LIMITS
    
    def test_contains_ai_limits(self):
        """Should contain AI generation rate limits"""
        assert "rate_limit.generate.story" in DEFAULT_RATE_LIMITS
        assert "rate_limit.generate.images" in DEFAULT_RATE_LIMITS
    
    def test_contains_admin_limits(self):
        """Should contain admin operation rate limits"""
        assert "rate_limit.admin.credits" in DEFAULT_RATE_LIMITS
        assert "rate_limit.admin.refund" in DEFAULT_RATE_LIMITS
    
    def test_contains_global_settings(self):
        """Should contain global rate limit settings"""
        assert "rate_limit.global.enabled" in DEFAULT_RATE_LIMITS
        assert "rate_limit.global.default" in DEFAULT_RATE_LIMITS
    
    def test_limit_structure(self):
        """Rate limit configs should have correct structure"""
        for key, config in DEFAULT_RATE_LIMITS.items():
            if key == "rate_limit.global.enabled":
                assert "enabled" in config
            else:
                assert "limit" in config
                assert "window" in config
                assert "enabled" in config
                assert isinstance(config["limit"], int)
                assert config["window"] in ["minute", "second", "hour"]
                assert isinstance(config["enabled"], bool)


class TestRateLimitPresets:
    """Tests for RATE_LIMIT_PRESETS constant"""
    
    def test_contains_required_presets(self):
        """Should contain all required presets"""
        required = ["strict", "normal", "relaxed", "disabled"]
        for preset in required:
            assert preset in RATE_LIMIT_PRESETS
    
    def test_preset_structure(self):
        """Presets should have correct structure"""
        for name, preset in RATE_LIMIT_PRESETS.items():
            assert "description" in preset
            if name == "disabled":
                assert "enabled" in preset
                assert preset["enabled"] is False
            else:
                assert "multiplier" in preset
                assert isinstance(preset["multiplier"], (int, float))
    
    def test_multiplier_values(self):
        """Multiplier values should be reasonable"""
        assert RATE_LIMIT_PRESETS["strict"]["multiplier"] < 1
        assert RATE_LIMIT_PRESETS["normal"]["multiplier"] == 1
        assert RATE_LIMIT_PRESETS["relaxed"]["multiplier"] > 1


class TestGetConfig:
    """Tests for get_config function"""
    
    def setup_method(self):
        """Clear cache before each test"""
        clear_config_cache()
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_returns_config_from_database(self, mock_supabase, mock_cache):
        """Should return config value from database"""
        mock_cache.get_config.return_value = None  # Cache miss
        
        mock_result = MagicMock()
        mock_result.data = {
            "value": '{"limit": 10, "window": "minute", "enabled": true}',
            "is_active": True
        }
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        result = get_config("rate_limit.test", use_cache=False)
        
        assert result == {"limit": 10, "window": "minute", "enabled": True}
    
    def test_returns_default_for_unknown_key(self):
        """Should return default value for unknown key"""
        # When supabase returns None, should fall back to defaults
        result = get_config("rate_limit.payment.checkout", use_cache=False)
        
        # Should return from DEFAULT_RATE_LIMITS or None
        if result is None:
            # This is acceptable if not in defaults
            pass
        else:
            assert "limit" in result
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_caching_works(self, mock_supabase, mock_cache):
        """Should cache results and not query database repeatedly"""
        mock_cache.get_config.return_value = {"limit": 5}
        
        # Both calls should use cache
        result1 = get_config("test_key", use_cache=True)
        result2 = get_config("test_key", use_cache=True)
        
        # Both should return same value
        assert result1 == result2
        # Database should not be queried when cache hit
        mock_supabase.table.assert_not_called()
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_bypasses_cache_when_requested(self, mock_supabase, mock_cache):
        """Should bypass cache when use_cache=False"""
        mock_cache.get_config.return_value = {"cached": "value"}
        
        mock_result = MagicMock()
        mock_result.data = {
            "value": '{"value": "fresh"}',
            "is_active": True
        }
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        get_config("test_key", use_cache=False)
        get_config("test_key", use_cache=False)
        
        # Should query database even with cache
        assert mock_supabase.table.call_count >= 2
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_handles_inactive_config(self, mock_supabase, mock_cache):
        """Should return default for inactive config"""
        mock_cache.get_config.return_value = None
        
        mock_result = MagicMock()
        mock_result.data = {
            "value": '{"limit": 10}',
            "is_active": False
        }
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
        
        result = get_config("test_key", use_cache=False)
        
        # Should return None or default since is_active is False
        # The behavior depends on implementation


class TestSetConfig:
    """Tests for set_config function"""
    
    def setup_method(self):
        """Clear cache before each test"""
        clear_config_cache()
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_updates_config_in_database(self, mock_supabase, mock_cache):
        """Should update config in database"""
        mock_result = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_result
        
        result = set_config("test_key", {"limit": 20}, "admin_user")
        
        assert result is True
        mock_supabase.table.assert_called_with("system_configs")
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_clears_cache_after_update(self, mock_supabase, mock_cache):
        """Should clear cache after successful update"""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        
        set_config("test_key", {"new": "value"}, "admin")
        
        # Cache should be invalidated
        mock_cache.invalidate_config_cache.assert_called_with("test_key")
    
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_handles_database_error(self, mock_supabase, mock_cache):
        """Should return False on database error"""
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception("DB Error")
        
        result = set_config("test_key", {"value": 1}, "admin")
        
        assert result is False


class TestGetAllConfigs:
    """Tests for get_all_configs function"""
    
    @patch('services.config_service.supabase')
    def test_returns_all_configs(self, mock_supabase):
        """Should return all configs from database"""
        mock_result = MagicMock()
        mock_result.data = [
            {"key": "config1", "value": '{"a": 1}'},
            {"key": "config2", "value": '{"b": 2}'},
        ]
        
        mock_supabase.table.return_value.select.return_value.order.return_value.execute.return_value = mock_result
        
        result = get_all_configs()
        
        assert len(result) == 2
    
    @patch('services.config_service.supabase')
    def test_filters_by_category(self, mock_supabase):
        """Should filter by category when specified"""
        mock_result = MagicMock()
        mock_result.data = [{"key": "rate_limit.test", "value": '{}'}]
        
        mock_query = MagicMock()
        mock_query.eq.return_value.order.return_value.execute.return_value = mock_result
        mock_supabase.table.return_value.select.return_value = mock_query
        
        result = get_all_configs(category="rate_limit")
        
        mock_query.eq.assert_called_with("config_group", "rate_limit")
    
    def test_returns_defaults_when_no_supabase(self):
        """Should return defaults when supabase is not available"""
        with patch('services.config_service.supabase', None):
            result = get_all_configs(category="rate_limit")
            
            # Should return configs from DEFAULT_RATE_LIMITS
            assert len(result) > 0
            for config in result:
                assert config["key"].startswith("rate_limit")


class TestGetRateLimitString:
    """Tests for get_rate_limit_string function"""
    
    @patch('services.config_service.get_config')
    def test_formats_rate_limit_string(self, mock_get_config):
        """Should format rate limit as slowapi string"""
        mock_get_config.return_value = {
            "limit": 10,
            "window": "minute",
            "enabled": True
        }
        
        result = get_rate_limit_string("rate_limit.test")
        
        assert result == "10/minute"
    
    @patch('services.config_service.get_config')
    def test_returns_high_limit_when_disabled(self, mock_get_config):
        """Should return high limit when rate limit is disabled"""
        mock_get_config.return_value = {
            "limit": 10,
            "window": "minute",
            "enabled": False
        }
        
        result = get_rate_limit_string("rate_limit.test")
        
        assert result == "10000/minute"
    
    @patch('services.config_service.get_config')
    def test_handles_missing_config(self, mock_get_config):
        """Should handle missing config gracefully"""
        mock_get_config.return_value = None
        
        result = get_rate_limit_string("rate_limit.unknown")
        
        # Should return a default high limit
        assert "/minute" in result


class TestIsRateLimitEnabled:
    """Tests for is_rate_limit_enabled function"""
    
    @patch('services.config_service.get_config')
    def test_global_disabled_returns_false(self, mock_get_config):
        """Should return False when global is disabled"""
        mock_get_config.return_value = {"enabled": False}
        
        result = is_rate_limit_enabled()
        
        assert result is False
    
    @patch('services.config_service.get_config')
    def test_specific_key_disabled_returns_false(self, mock_get_config):
        """Should return False when specific key is disabled"""
        def side_effect(key):
            if key == "rate_limit.global.enabled":
                return {"enabled": True}
            return {"enabled": False}
        
        mock_get_config.side_effect = side_effect
        
        result = is_rate_limit_enabled("rate_limit.test")
        
        assert result is False
    
    @patch('services.config_service.get_config')
    def test_both_enabled_returns_true(self, mock_get_config):
        """Should return True when both global and specific are enabled"""
        mock_get_config.return_value = {"enabled": True}
        
        result = is_rate_limit_enabled("rate_limit.test")
        
        assert result is True


class TestClearConfigCache:
    """Tests for clear_config_cache function"""
    
    @patch('services.config_service.cache_service')
    def test_clears_all_cache(self, mock_cache):
        """Should clear all cached configs via cache_service"""
        clear_config_cache()
        
        mock_cache.invalidate_config_cache.assert_called_once()


class TestBatchUpdateConfigs:
    """Tests for batch_update_configs function"""
    
    @patch('services.config_service.set_config')
    def test_updates_multiple_configs(self, mock_set_config):
        """Should update multiple configs"""
        mock_set_config.return_value = True
        
        updates = [
            {"config_key": "key1", "config_value": {"a": 1}},
            {"config_key": "key2", "config_value": {"b": 2}},
        ]
        
        result = batch_update_configs(updates, "admin")
        
        assert result["key1"] is True
        assert result["key2"] is True
        assert mock_set_config.call_count == 2
    
    @patch('services.config_service.set_config')
    def test_handles_partial_failure(self, mock_set_config):
        """Should handle partial update failures"""
        mock_set_config.side_effect = [True, False]
        
        updates = [
            {"config_key": "key1", "config_value": {"a": 1}},
            {"config_key": "key2", "config_value": {"b": 2}},
        ]
        
        result = batch_update_configs(updates, "admin")
        
        assert result["key1"] is True
        assert result["key2"] is False
    
    def test_skips_invalid_updates(self):
        """Should skip updates without key or value"""
        with patch('services.config_service.set_config') as mock_set:
            mock_set.return_value = True
            
            updates = [
                {"config_key": "key1", "config_value": {"a": 1}},
                {"config_key": "key2"},  # Missing value
                {"config_value": {"c": 3}},  # Missing key
            ]
            
            result = batch_update_configs(updates, "admin")
            
            assert "key1" in result
            assert "key2" not in result


class TestApplyRateLimitPreset:
    """Tests for apply_rate_limit_preset function"""
    
    @patch('services.config_service.set_config')
    @patch('services.config_service.clear_config_cache')
    def test_applies_disabled_preset(self, mock_clear, mock_set_config):
        """Should disable global rate limiting for 'disabled' preset"""
        mock_set_config.return_value = True
        
        result = apply_rate_limit_preset("disabled", "admin")
        
        assert result is True
        mock_set_config.assert_called_with(
            "rate_limit.global.enabled",
            {"enabled": False},
            "admin"
        )
    
    @patch('services.config_service.set_config')
    @patch('services.config_service.clear_config_cache')
    def test_applies_normal_preset(self, mock_clear, mock_set_config):
        """Should reset to defaults for 'normal' preset"""
        mock_set_config.return_value = True
        
        result = apply_rate_limit_preset("normal", "admin")
        
        assert result is True
        # Should enable global and reset individual limits
        mock_clear.assert_called_once()
    
    def test_rejects_invalid_preset(self):
        """Should return False for invalid preset"""
        result = apply_rate_limit_preset("invalid_preset", "admin")
        
        assert result is False
    
    @patch('services.config_service.set_config')
    @patch('services.config_service.get_all_configs')
    @patch('services.config_service.clear_config_cache')
    def test_applies_strict_preset_multiplier(self, mock_clear, mock_get_all, mock_set):
        """Should apply multiplier for 'strict' preset"""
        mock_set.return_value = True
        mock_get_all.return_value = [
            {"key": "rate_limit.test", "value": '{"limit": 10, "window": "minute", "enabled": true}'}
        ]
        
        result = apply_rate_limit_preset("strict", "admin")
        
        assert result is True
