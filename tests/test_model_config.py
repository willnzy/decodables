"""
AI Model Config Tests
AI 模型配置测试

核心业务规则:
1. 模型配置从 system_configs 获取
2. 支持用户文本/图像模型
3. 支持 Admin 分析模型
4. 提供商可用性检查
"""

import pytest
from unittest.mock import patch


class TestDefaultConfigs:
    def test_default_text_config(self):
        from shared.ai.model_config import DEFAULT_TEXT_CONFIG
        assert DEFAULT_TEXT_CONFIG["provider"] == "openai"
        assert DEFAULT_TEXT_CONFIG["model"] == "gpt-4o-mini"
        assert "fallback" in DEFAULT_TEXT_CONFIG

    def test_default_image_config(self):
        from shared.ai.model_config import DEFAULT_IMAGE_CONFIG
        assert DEFAULT_IMAGE_CONFIG["provider"] == "fal"
        assert "models" in DEFAULT_IMAGE_CONFIG
        assert "free" in DEFAULT_IMAGE_CONFIG["models"]

    def test_default_admin_config(self):
        from shared.ai.model_config import DEFAULT_ADMIN_CONFIG
        assert DEFAULT_ADMIN_CONFIG["provider"] == "openai"
        assert DEFAULT_ADMIN_CONFIG["model"] == "gpt-4o"

    def test_default_enabled_providers(self):
        from shared.ai.model_config import DEFAULT_ENABLED_PROVIDERS
        assert DEFAULT_ENABLED_PROVIDERS["openai"] is True
        assert DEFAULT_ENABLED_PROVIDERS["fal"] is True


class TestGetTextModelConfig:
    @patch('services.ai.model_config.get_config')
    def test_returns_config_from_db(self, mock_get_config):
        from shared.ai.model_config import get_text_model_config
        mock_get_config.return_value = {"provider": "qwen", "model": "qwen-plus"}
        
        result = get_text_model_config()
        
        assert result["provider"] == "qwen"
        mock_get_config.assert_called_with("ai_model.user.text_reasoning")

    @patch('services.ai.model_config.get_config')
    def test_returns_default_when_no_config(self, mock_get_config):
        from shared.ai.model_config import get_text_model_config
        mock_get_config.return_value = None
        
        result = get_text_model_config()
        
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o-mini"


class TestGetImageModelConfig:
    @patch('services.ai.model_config.get_config')
    def test_returns_config_with_tier_model(self, mock_get_config):
        from shared.ai.model_config import get_image_model_config
        mock_get_config.return_value = {
            "provider": "fal",
            "models": {"free": "flux-schnell", "pro": "flux-dev"},
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
        
        result = get_image_model_config("pro")
        
        assert result["provider"] == "fal"
        assert result["model"] == "flux-dev"

    @patch('services.ai.model_config.get_config')
    def test_uses_free_model_by_default(self, mock_get_config):
        from shared.ai.model_config import get_image_model_config
        mock_get_config.return_value = None
        
        result = get_image_model_config()
        
        assert result["model"] == "flux-schnell"

    @patch('services.ai.model_config.get_config')
    def test_returns_default_when_no_config(self, mock_get_config):
        from shared.ai.model_config import get_image_model_config
        mock_get_config.return_value = None
        
        result = get_image_model_config("free")
        
        assert result["provider"] == "fal"


class TestGetAdminModelConfig:
    @patch('services.ai.model_config.get_config')
    def test_returns_config_from_db(self, mock_get_config):
        from shared.ai.model_config import get_admin_model_config
        mock_get_config.return_value = {"provider": "openai", "model": "gpt-4-turbo"}
        
        result = get_admin_model_config()
        
        assert result["model"] == "gpt-4-turbo"

    @patch('services.ai.model_config.get_config')
    def test_returns_default_when_no_config(self, mock_get_config):
        from shared.ai.model_config import get_admin_model_config
        mock_get_config.return_value = None
        
        result = get_admin_model_config()
        
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o"


class TestGetEnabledProviders:
    @patch('services.ai.model_config.get_config')
    def test_returns_config_from_db(self, mock_get_config):
        from shared.ai.model_config import get_enabled_providers
        mock_get_config.return_value = {"openai": True, "qwen": True}
        
        result = get_enabled_providers()
        
        assert result["openai"] is True
        assert result["qwen"] is True

    @patch('services.ai.model_config.get_config')
    def test_returns_default_when_no_config(self, mock_get_config):
        from shared.ai.model_config import get_enabled_providers
        mock_get_config.return_value = None
        
        result = get_enabled_providers()
        
        assert result["openai"] is True
        assert result["qwen"] is False


class TestGetProviderModels:
    @patch('services.ai.model_config.get_config')
    def test_returns_provider_models(self, mock_get_config):
        from shared.ai.model_config import get_provider_models
        mock_get_config.return_value = {
            "openai": {"text": ["gpt-4o", "gpt-4o-mini"], "image": ["dall-e-3"]}
        }
        
        result = get_provider_models("openai")
        
        assert "gpt-4o" in result["text"]

    @patch('services.ai.model_config.get_config')
    def test_returns_empty_for_unknown_provider(self, mock_get_config):
        from shared.ai.model_config import get_provider_models
        mock_get_config.return_value = {"openai": {}}
        
        result = get_provider_models("unknown")
        
        assert result == {}


class TestGetProviderTimeout:
    @patch('services.ai.model_config.get_config')
    def test_returns_configured_timeout(self, mock_get_config):
        from shared.ai.model_config import get_provider_timeout
        mock_get_config.return_value = {"openai": {"text": 30, "image": 120}}
        
        result = get_provider_timeout("openai", "text")
        
        assert result == 30

    @patch('services.ai.model_config.get_config')
    def test_returns_default_text_timeout(self, mock_get_config):
        from shared.ai.model_config import get_provider_timeout
        mock_get_config.return_value = None
        
        result = get_provider_timeout("openai", "text")
        
        assert result == 60

    @patch('services.ai.model_config.get_config')
    def test_returns_default_image_timeout(self, mock_get_config):
        from shared.ai.model_config import get_provider_timeout
        mock_get_config.return_value = None
        
        result = get_provider_timeout("fal", "image")
        
        assert result == 180


class TestGetModelCost:
    @patch('services.ai.model_config.get_config')
    def test_returns_configured_cost(self, mock_get_config):
        from shared.ai.model_config import get_model_cost
        mock_get_config.return_value = {"openai": {"gpt-4o": 2.50, "gpt-4o-mini": 0.15}}
        
        result = get_model_cost("openai", "gpt-4o")
        
        assert result == 2.50

    @patch('services.ai.model_config.get_config')
    def test_returns_zero_for_unknown_model(self, mock_get_config):
        from shared.ai.model_config import get_model_cost
        mock_get_config.return_value = {}
        
        result = get_model_cost("unknown", "unknown-model")
        
        assert result == 0.0


class TestGetRetryConfig:
    @patch('services.ai.model_config.get_config')
    def test_returns_configured_retry(self, mock_get_config):
        from shared.ai.model_config import get_retry_config
        mock_get_config.return_value = {"max_retries": 5, "base_delay_ms": 2000}
        
        result = get_retry_config()
        
        assert result["max_retries"] == 5

    @patch('services.ai.model_config.get_config')
    def test_returns_default_retry(self, mock_get_config):
        from shared.ai.model_config import get_retry_config
        mock_get_config.return_value = None
        
        result = get_retry_config()
        
        assert result["max_retries"] == 3
        assert result["base_delay_ms"] == 1000


class TestIsProviderEnabled:
    @patch('services.ai.model_config.get_enabled_providers')
    def test_returns_true_when_enabled(self, mock_get_providers):
        from shared.ai.model_config import is_provider_enabled
        mock_get_providers.return_value = {"openai": True}
        
        result = is_provider_enabled("openai")
        
        assert result is True

    @patch('services.ai.model_config.get_enabled_providers')
    def test_returns_false_when_disabled(self, mock_get_providers):
        from shared.ai.model_config import is_provider_enabled
        mock_get_providers.return_value = {"openai": False}
        
        result = is_provider_enabled("openai")
        
        assert result is False

    @patch('services.ai.model_config.get_enabled_providers')
    def test_returns_false_for_unknown(self, mock_get_providers):
        from shared.ai.model_config import is_provider_enabled
        mock_get_providers.return_value = {}
        
        result = is_provider_enabled("unknown")
        
        assert result is False


class TestUtilityFunctions:
    def test_get_fallback_config(self):
        from shared.ai.model_config import get_fallback_config
        config = {"provider": "openai", "fallback": {"provider": "qwen", "model": "qwen-plus"}}
        
        result = get_fallback_config(config)
        
        assert result["provider"] == "qwen"

    def test_get_fallback_config_returns_none(self):
        from shared.ai.model_config import get_fallback_config
        config = {"provider": "openai"}
        
        result = get_fallback_config(config)
        
        assert result is None

    def test_should_show_provider_true(self):
        from shared.ai.model_config import should_show_provider
        config = {"provider": "openai", "show_provider": True}
        
        result = should_show_provider(config)
        
        assert result is True

    def test_should_show_provider_false_by_default(self):
        from shared.ai.model_config import should_show_provider
        config = {"provider": "openai"}
        
        result = should_show_provider(config)
        
        assert result is False


class TestGetAllProviderModels:
    @patch('services.ai.model_config.get_config')
    def test_returns_all_models(self, mock_get_config):
        from shared.ai.model_config import get_all_provider_models
        mock_get_config.return_value = {
            "openai": {"text": ["gpt-4o"]},
            "fal": {"image": ["flux-schnell"]}
        }
        
        result = get_all_provider_models()
        
        assert "openai" in result
        assert "fal" in result

    @patch('services.ai.model_config.get_config')
    def test_returns_empty_when_no_config(self, mock_get_config):
        from shared.ai.model_config import get_all_provider_models
        mock_get_config.return_value = None
        
        result = get_all_provider_models()
        
        assert result == {}
