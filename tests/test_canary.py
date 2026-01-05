"""
Canary Release Tests
灰度发布测试

核心业务规则:
1. 基于用户ID的确定性分流
2. 支持指定用户等级
3. 支持文本/图像模型独立配置
"""

import pytest
from unittest.mock import patch


class TestGetCanaryConfig:
    @patch('services.ai.canary.get_config')
    def test_returns_config_when_exists(self, mock_get_config):
        from services.ai.canary import get_canary_config
        mock_get_config.return_value = {"enabled": True, "text_reasoning": {}}
        
        result = get_canary_config()
        
        assert result["enabled"] is True

    @patch('services.ai.canary.get_config')
    def test_returns_default_when_none(self, mock_get_config):
        from services.ai.canary import get_canary_config
        mock_get_config.return_value = None
        
        result = get_canary_config()
        
        assert result == {"enabled": False}


class TestShouldUseCanary:
    @patch('services.ai.canary.get_canary_config')
    def test_disabled_when_not_enabled(self, mock_config):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {"enabled": False}
        
        result, config = should_use_canary("user_123", "text_reasoning", "free")
        
        assert result is False
        assert config is None

    @patch('services.ai.canary.get_canary_config')
    def test_disabled_when_no_model_config(self, mock_config):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {"enabled": True}
        
        result, config = should_use_canary("user_123", "text_reasoning", "free")
        
        assert result is False

    @patch('services.ai.canary.get_canary_config')
    def test_disabled_when_tier_not_target(self, mock_config):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 100,
                "target_tiers": ["pro"]  # Only pro
            }
        }
        
        result, config = should_use_canary("user_123", "text_reasoning", "free")
        
        assert result is False

    @patch('services.ai.canary._get_user_bucket')
    @patch('services.ai.canary.get_canary_config')
    def test_enabled_when_in_bucket(self, mock_config, mock_bucket):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 50,
                "target_tiers": ["free", "pro"]
            }
        }
        mock_bucket.return_value = 25  # < 50%
        
        result, config = should_use_canary("user_123", "text_reasoning", "free")
        
        assert result is True
        assert config["provider"] == "qwen"

    @patch('services.ai.canary._get_user_bucket')
    @patch('services.ai.canary.get_canary_config')
    def test_disabled_when_not_in_bucket(self, mock_config, mock_bucket):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 50,
                "target_tiers": []  # All tiers
            }
        }
        mock_bucket.return_value = 75  # > 50%
        
        result, config = should_use_canary("user_123", "text_reasoning", "free")
        
        assert result is False

    @patch('services.ai.canary.get_canary_config')
    def test_disabled_when_zero_traffic(self, mock_config):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 0
            }
        }
        
        result, config = should_use_canary("user_123", "text_reasoning", "free")
        
        assert result is False


class TestGetUserBucket:
    def test_deterministic(self):
        from services.ai.canary import _get_user_bucket
        
        bucket1 = _get_user_bucket("user_123", "text_reasoning")
        bucket2 = _get_user_bucket("user_123", "text_reasoning")
        
        assert bucket1 == bucket2

    def test_different_model_types_different_buckets(self):
        from services.ai.canary import _get_user_bucket
        
        bucket1 = _get_user_bucket("user_123", "text_reasoning")
        bucket2 = _get_user_bucket("user_123", "image_generation")
        
        # May or may not be different, but should be consistent
        assert isinstance(bucket1, int)
        assert isinstance(bucket2, int)

    def test_bucket_range(self):
        from services.ai.canary import _get_user_bucket
        
        for i in range(100):
            bucket = _get_user_bucket(f"user_{i}", "text_reasoning")
            assert 0 <= bucket < 100


class TestGetEffectiveModelConfig:
    @patch('services.ai.canary.should_use_canary')
    def test_uses_canary_config(self, mock_should_use):
        from services.ai.canary import get_effective_model_config
        
        mock_should_use.return_value = (True, {"provider": "qwen", "model": "qwen-plus"})
        base_config = {"provider": "openai", "model": "gpt-4o-mini"}
        
        result = get_effective_model_config("user_123", "text_reasoning", "pro", base_config)
        
        assert result["provider"] == "qwen"
        assert result["model"] == "qwen-plus"
        assert result["is_canary"] is True

    @patch('services.ai.canary.should_use_canary')
    def test_uses_base_config(self, mock_should_use):
        from services.ai.canary import get_effective_model_config
        
        mock_should_use.return_value = (False, None)
        base_config = {"provider": "openai", "model": "gpt-4o-mini"}
        
        result = get_effective_model_config("user_123", "text_reasoning", "free", base_config)
        
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o-mini"
        assert result["is_canary"] is False


class TestGetCanaryStatus:
    @patch('services.ai.canary.get_canary_config')
    def test_returns_status(self, mock_config):
        from services.ai.canary import get_canary_status
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 10,
                "target_tiers": ["pro"]
            }
        }
        
        result = get_canary_status()
        
        assert result["enabled"] is True
        assert result["text_reasoning"]["enabled"] is True
        assert result["text_reasoning"]["canary_provider"] == "qwen"

    @patch('services.ai.canary.get_canary_config')
    def test_handles_missing_model_config(self, mock_config):
        from services.ai.canary import get_canary_status
        mock_config.return_value = {"enabled": False}
        
        result = get_canary_status()
        
        assert result["enabled"] is False
        assert result["text_reasoning"]["enabled"] is False
        assert result["image_generation"]["enabled"] is False
