"""
Config Service Tests
"""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestDefaultRateLimits:
    def test_payment_rate_limits_defined(self):
        from services.config_service import DEFAULT_RATE_LIMITS
        assert "rate_limit.payment.checkout" in DEFAULT_RATE_LIMITS
        assert "rate_limit.payment.portal" in DEFAULT_RATE_LIMITS

    def test_ai_rate_limits_defined(self):
        from services.config_service import DEFAULT_RATE_LIMITS
        assert "rate_limit.generate.story" in DEFAULT_RATE_LIMITS
        assert "rate_limit.generate.images" in DEFAULT_RATE_LIMITS

    def test_global_settings_defined(self):
        from services.config_service import DEFAULT_RATE_LIMITS
        assert "rate_limit.global.default" in DEFAULT_RATE_LIMITS
        assert "rate_limit.global.enabled" in DEFAULT_RATE_LIMITS


class TestRateLimitPresets:
    def test_presets_defined(self):
        from services.config_service import RATE_LIMIT_PRESETS
        assert "strict" in RATE_LIMIT_PRESETS
        assert "normal" in RATE_LIMIT_PRESETS
        assert "relaxed" in RATE_LIMIT_PRESETS
        assert "disabled" in RATE_LIMIT_PRESETS

    def test_strict_preset_multiplier(self):
        from services.config_service import RATE_LIMIT_PRESETS
        assert RATE_LIMIT_PRESETS["strict"]["multiplier"] == 0.5

    def test_normal_preset_multiplier(self):
        from services.config_service import RATE_LIMIT_PRESETS
        assert RATE_LIMIT_PRESETS["normal"]["multiplier"] == 1.0

    def test_relaxed_preset_multiplier(self):
        from services.config_service import RATE_LIMIT_PRESETS
        assert RATE_LIMIT_PRESETS["relaxed"]["multiplier"] == 2.0

    def test_disabled_preset(self):
        from services.config_service import RATE_LIMIT_PRESETS
        assert RATE_LIMIT_PRESETS["disabled"]["enabled"] is False


class TestGetConfig:
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_get_config_from_cache(self, mock_supabase, mock_cache):
        from services.config_service import get_config
        mock_cache.get_config.return_value = {"limit": 10, "window": "minute", "enabled": True}
        result = get_config("rate_limit.test")
        mock_cache.get_config.assert_called_once_with("rate_limit.test")
        assert result["limit"] == 10

    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase', None)
    def test_get_config_returns_default_when_no_db(self, mock_cache):
        from services.config_service import get_config, DEFAULT_RATE_LIMITS
        mock_cache.get_config.return_value = None
        result = get_config("rate_limit.payment.checkout")
        assert result == DEFAULT_RATE_LIMITS["rate_limit.payment.checkout"]


class TestSetConfig:
    @patch('services.config_service.cache_service')
    @patch('services.config_service.supabase')
    def test_set_config_success(self, mock_supabase, mock_cache):
        from services.config_service import set_config
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
        result = set_config("rate_limit.test", {"limit": 50}, "admin_123")
        assert result is True
        mock_cache.invalidate_config_cache.assert_called_with("rate_limit.test")

    @patch('services.config_service.supabase', None)
    def test_set_config_fails_without_db(self):
        from services.config_service import set_config
        result = set_config("rate_limit.test", {"limit": 50})
        assert result is False


class TestGetAllConfigs:
    @patch('services.config_service.supabase', None)
    def test_get_all_configs_returns_defaults_without_db(self):
        from services.config_service import get_all_configs
        result = get_all_configs()
        assert len(result) > 0

    @patch('services.config_service.supabase', None)
    def test_get_all_configs_filter_by_category(self):
        from services.config_service import get_all_configs
        result = get_all_configs("rate_limit")
        assert all(item["key"].startswith("rate_limit.") for item in result)


class TestGetRateLimitString:
    @patch('services.config_service.get_config')
    def test_get_rate_limit_string_enabled(self, mock_get_config):
        from services.config_service import get_rate_limit_string
        mock_get_config.return_value = {"limit": 10, "window": "minute", "enabled": True}
        result = get_rate_limit_string("rate_limit.test")
        assert result == "10/minute"

    @patch('services.config_service.get_config')
    def test_get_rate_limit_string_disabled(self, mock_get_config):
        from services.config_service import get_rate_limit_string
        mock_get_config.return_value = {"limit": 10, "window": "minute", "enabled": False}
        result = get_rate_limit_string("rate_limit.test")
        assert result == "10000/minute"

    @patch('services.config_service.get_config')
    def test_get_rate_limit_string_no_config(self, mock_get_config):
        from services.config_service import get_rate_limit_string
        mock_get_config.return_value = None
        result = get_rate_limit_string("rate_limit.test")
        assert result == "10000/minute"


class TestIsRateLimitEnabled:
    @patch('services.config_service.get_config')
    def test_is_enabled_when_global_enabled(self, mock_get_config):
        from services.config_service import is_rate_limit_enabled
        mock_get_config.return_value = {"enabled": True}
        result = is_rate_limit_enabled()
        assert result is True

    @patch('services.config_service.get_config')
    def test_is_disabled_when_global_disabled(self, mock_get_config):
        from services.config_service import is_rate_limit_enabled
        mock_get_config.return_value = {"enabled": False}
        result = is_rate_limit_enabled()
        assert result is False


class TestClearConfigCache:
    @patch('services.config_service.cache_service')
    def test_clear_config_cache(self, mock_cache):
        from services.config_service import clear_config_cache
        clear_config_cache()
        mock_cache.invalidate_config_cache.assert_called_once()


class TestBatchUpdateConfigs:
    @patch('services.config_service.set_config')
    def test_batch_update_success(self, mock_set_config):
        from services.config_service import batch_update_configs
        mock_set_config.return_value = True
        updates = [
            {"config_key": "test1", "config_value": {"limit": 10}},
            {"config_key": "test2", "config_value": {"limit": 20}},
        ]
        result = batch_update_configs(updates, "admin_123")
        assert result["test1"] is True
        assert result["test2"] is True

    @patch('services.config_service.set_config')
    def test_batch_update_skips_invalid(self, mock_set_config):
        from services.config_service import batch_update_configs
        mock_set_config.return_value = True
        updates = [
            {"config_key": "test1", "config_value": {"limit": 10}},
            {"config_value": {"limit": 20}},
        ]
        result = batch_update_configs(updates)
        assert "test1" in result
        assert mock_set_config.call_count == 1


class TestApplyRateLimitPreset:
    @patch('services.config_service.clear_config_cache')
    @patch('services.config_service.set_config')
    def test_apply_disabled_preset(self, mock_set_config, mock_clear_cache):
        from services.config_service import apply_rate_limit_preset
        mock_set_config.return_value = True
        result = apply_rate_limit_preset("disabled", "admin_123")
        assert result is True

    def test_apply_invalid_preset(self):
        from services.config_service import apply_rate_limit_preset
        result = apply_rate_limit_preset("invalid_preset")
        assert result is False

    @patch('services.config_service.clear_config_cache')
    @patch('services.config_service.set_config')
    def test_apply_normal_preset(self, mock_set_config, mock_clear_cache):
        from services.config_service import apply_rate_limit_preset
        mock_set_config.return_value = True
        result = apply_rate_limit_preset("normal", "admin_123")
        assert result is True
        mock_clear_cache.assert_called_once()
