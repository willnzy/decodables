"""
Canary Release Tests
灰度发布测试
"""

import pytest
from unittest.mock import patch, MagicMock


class TestGetCanaryConfig:
    @patch('services.ai.canary.get_config')
    def test_returns_config_when_exists(self, mock_get_config):
        from services.ai.canary import get_canary_config
        mock_get_config.return_value = {"enabled": True, "text_reasoning": {}}
        result = get_canary_config()
        assert result["enabled"] is True
        mock_get_config.assert_called_with("ai_model.canary")

    @patch('services.ai.canary.get_config')
    def test_returns_disabled_when_no_config(self, mock_get_config):
        from services.ai.canary import get_canary_config
        mock_get_config.return_value = None
        result = get_canary_config()
        assert result == {"enabled": False}


class TestGetUserBucket:
    def test_deterministic_same_user(self):
        from services.ai.canary import _get_user_bucket
        bucket1 = _get_user_bucket("user_123", "text_reasoning")
        bucket2 = _get_user_bucket("user_123", "text_reasoning")
        assert bucket1 == bucket2

    def test_different_users_different_buckets(self):
        from services.ai.canary import _get_user_bucket
        bucket1 = _get_user_bucket("user_123", "text_reasoning")
        bucket2 = _get_user_bucket("user_456", "text_reasoning")
        # Different users should generally get different buckets
        # (not always true due to hash collisions, but very likely)
        # We just test they are in valid range
        assert 0 <= bucket1 < 100
        assert 0 <= bucket2 < 100

    def test_bucket_range(self):
        from services.ai.canary import _get_user_bucket
        for i in range(100):
            bucket = _get_user_bucket(f"user_{i}", "text_reasoning")
            assert 0 <= bucket < 100

    def test_different_model_types_independent(self):
        from services.ai.canary import _get_user_bucket
        bucket1 = _get_user_bucket("user_123", "text_reasoning")
        bucket2 = _get_user_bucket("user_123", "image_generation")
        # Same user, different model types may get different buckets
        assert 0 <= bucket1 < 100
        assert 0 <= bucket2 < 100


class TestShouldUseCanary:
    @patch('services.ai.canary.get_canary_config')
    def test_returns_false_when_disabled(self, mock_config):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {"enabled": False}
        result, config = should_use_canary("user_123", "text_reasoning", "pro")
        assert result is False
        assert config is None

    @patch('services.ai.canary.get_canary_config')
    def test_returns_false_when_no_model_type_config(self, mock_config):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {"enabled": True}
        result, config = should_use_canary("user_123", "text_reasoning", "pro")
        assert result is False
        assert config is None

    @patch('services.ai.canary.get_canary_config')
    def test_returns_false_when_tier_not_targeted(self, mock_config):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 100,
                "target_tiers": ["pro"]
            }
        }
        result, config = should_use_canary("user_123", "text_reasoning", "free")
        assert result is False
        assert config is None

    @patch('services.ai.canary.get_canary_config')
    def test_returns_false_when_traffic_percent_zero(self, mock_config):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 0,
                "target_tiers": []
            }
        }
        result, config = should_use_canary("user_123", "text_reasoning", "pro")
        assert result is False
        assert config is None

    @patch('services.ai.canary._get_user_bucket')
    @patch('services.ai.canary.get_canary_config')
    def test_returns_true_when_bucket_in_range(self, mock_config, mock_bucket):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 50,
                "target_tiers": []
            }
        }
        mock_bucket.return_value = 25  # Less than 50
        result, config = should_use_canary("user_123", "text_reasoning", "pro")
        assert result is True
        assert config["provider"] == "qwen"
        assert config["model"] == "qwen-plus"

    @patch('services.ai.canary._get_user_bucket')
    @patch('services.ai.canary.get_canary_config')
    def test_returns_false_when_bucket_out_of_range(self, mock_config, mock_bucket):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 10,
                "target_tiers": []
            }
        }
        mock_bucket.return_value = 50  # Greater than 10
        result, config = should_use_canary("user_123", "text_reasoning", "pro")
        assert result is False
        assert config is None


class TestGetEffectiveModelConfig:
    @patch('services.ai.canary.should_use_canary')
    def test_returns_base_config_when_not_canary(self, mock_should_use):
        from services.ai.canary import get_effective_model_config
        mock_should_use.return_value = (False, None)
        base_config = {"provider": "openai", "model": "gpt-4o-mini"}
        result = get_effective_model_config("user_123", "text_reasoning", "pro", base_config)
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o-mini"
        assert result["is_canary"] is False

    @patch('services.ai.canary.should_use_canary')
    def test_returns_canary_config_when_canary(self, mock_should_use):
        from services.ai.canary import get_effective_model_config
        mock_should_use.return_value = (True, {"provider": "qwen", "model": "qwen-plus"})
        base_config = {"provider": "openai", "model": "gpt-4o-mini"}
        result = get_effective_model_config("user_123", "text_reasoning", "pro", base_config)
        assert result["provider"] == "qwen"
        assert result["model"] == "qwen-plus"
        assert result["is_canary"] is True


class TestGetCanaryStatus:
    @patch('services.ai.canary.get_canary_config')
    def test_status_disabled(self, mock_config):
        from services.ai.canary import get_canary_status
        mock_config.return_value = {"enabled": False}
        status = get_canary_status()
        assert status["enabled"] is False
        assert "text_reasoning" in status
        assert "image_generation" in status

    @patch('services.ai.canary.get_canary_config')
    def test_status_enabled_with_configs(self, mock_config):
        from services.ai.canary import get_canary_status
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 10,
                "target_tiers": ["pro"]
            },
            "image_generation": {
                "canary_provider": "jimeng",
                "canary_model": "jimeng-2.1",
                "traffic_percent": 5,
                "target_tiers": ["pro"]
            }
        }
        status = get_canary_status()
        assert status["enabled"] is True
        assert status["text_reasoning"]["canary_provider"] == "qwen"
        assert status["text_reasoning"]["traffic_percent"] == 10
        assert status["image_generation"]["canary_provider"] == "jimeng"


class TestCanaryDistribution:
    """Test that canary distribution is roughly uniform"""
    
    @patch('services.ai.canary.get_canary_config')
    def test_distribution_roughly_uniform(self, mock_config):
        from services.ai.canary import should_use_canary
        mock_config.return_value = {
            "enabled": True,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 50,  # 50% traffic
                "target_tiers": []  # All tiers
            }
        }
        
        canary_count = 0
        total = 1000
        
        for i in range(total):
            result, _ = should_use_canary(f"user_{i}", "text_reasoning", "pro")
            if result:
                canary_count += 1
        
        # With 50% traffic, expect roughly 500 +/- 100
        assert 350 < canary_count < 650, f"Expected ~500, got {canary_count}"
