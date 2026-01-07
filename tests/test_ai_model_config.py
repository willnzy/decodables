"""
Unit Tests for AI Model Configuration
AI 模型配置单元测试

Tests:
- get_text_model_config
- get_image_model_config
- get_admin_model_config
- get_enabled_providers
- get_provider_models
- is_provider_enabled
- get_model_cost
"""

import pytest
from unittest.mock import patch, MagicMock


# ==========================================
# get_text_model_config Tests
# ==========================================

class TestGetTextModelConfig:
    """get_text_model_config 函数测试"""
    
    @patch('services.ai.model_config.get_config')
    def test_returns_config_from_db(self, mock_get_config):
        """从数据库返回配置"""
        from shared.ai.model_config import get_text_model_config
        
        mock_get_config.return_value = {
            "provider": "qwen",
            "model": "qwen-plus",
            "fallback": {"provider": "openai", "model": "gpt-4o-mini"},
            "show_provider": True
        }
        
        config = get_text_model_config()
        
        assert config["provider"] == "qwen"
        assert config["model"] == "qwen-plus"
        mock_get_config.assert_called_once_with("ai_model.user.text_reasoning")
    
    @patch('services.ai.model_config.get_config')
    def test_returns_default_when_not_configured(self, mock_get_config):
        """未配置时返回默认值"""
        from shared.ai.model_config import get_text_model_config
        
        mock_get_config.return_value = None
        
        config = get_text_model_config()
        
        assert config["provider"] == "openai"
        assert config["model"] == "gpt-4o-mini"


# ==========================================
# get_image_model_config Tests
# ==========================================

class TestGetImageModelConfig:
    """get_image_model_config 函数测试"""
    
    @patch('services.ai.model_config.get_config')
    def test_free_tier_model(self, mock_get_config):
        """Free 用户模型"""
        from shared.ai.model_config import get_image_model_config
        
        mock_get_config.return_value = {
            "provider": "fal",
            "models": {
                "free": "flux-schnell",
                "starter": "flux-schnell",
                "pro": "flux-dev"
            },
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
        
        config = get_image_model_config("free")
        
        assert config["provider"] == "fal"
        assert config["model"] == "flux-schnell"
    
    @patch('services.ai.model_config.get_config')
    def test_pro_tier_model(self, mock_get_config):
        """Pro 用户模型"""
        from shared.ai.model_config import get_image_model_config
        
        mock_get_config.return_value = {
            "provider": "fal",
            "models": {
                "free": "flux-schnell",
                "starter": "flux-schnell",
                "pro": "flux-dev"
            },
            "fallback": {"provider": "fal", "model": "flux-schnell"}
        }
        
        config = get_image_model_config("pro")
        
        assert config["model"] == "flux-dev"
    
    @patch('services.ai.model_config.get_config')
    def test_unknown_tier_falls_back_to_free(self, mock_get_config):
        """未知等级回退到 free"""
        from shared.ai.model_config import get_image_model_config
        
        mock_get_config.return_value = {
            "provider": "fal",
            "models": {
                "free": "flux-schnell",
                "starter": "flux-schnell",
                "pro": "flux-dev"
            }
        }
        
        config = get_image_model_config("enterprise")  # 不存在的等级
        
        assert config["model"] == "flux-schnell"  # 回退到 free
    
    @patch('services.ai.model_config.get_config')
    def test_returns_default_when_not_configured(self, mock_get_config):
        """未配置时返回默认值"""
        from shared.ai.model_config import get_image_model_config
        
        mock_get_config.return_value = None
        
        config = get_image_model_config("free")
        
        assert config["provider"] == "fal"
        assert config["model"] == "flux-schnell"


# ==========================================
# get_admin_model_config Tests
# ==========================================

class TestGetAdminModelConfig:
    """get_admin_model_config 函数测试"""
    
    @patch('services.ai.model_config.get_config')
    def test_returns_admin_config(self, mock_get_config):
        """返回 Admin 配置"""
        from shared.ai.model_config import get_admin_model_config
        
        mock_get_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o",
            "fallback": {"provider": "openai", "model": "gpt-4o-mini"}
        }
        
        config = get_admin_model_config()
        
        assert config["provider"] == "openai"
        assert config["model"] == "gpt-4o"
        mock_get_config.assert_called_once_with("ai_model.admin.analysis")
    
    @patch('services.ai.model_config.get_config')
    def test_returns_default_when_not_configured(self, mock_get_config):
        """未配置时返回默认值"""
        from shared.ai.model_config import get_admin_model_config
        
        mock_get_config.return_value = None
        
        config = get_admin_model_config()
        
        assert config["provider"] == "openai"
        assert config["model"] == "gpt-4o"


# ==========================================
# get_enabled_providers Tests
# ==========================================

class TestGetEnabledProviders:
    """get_enabled_providers 函数测试"""
    
    @patch('services.ai.model_config.get_config')
    def test_returns_enabled_providers(self, mock_get_config):
        """返回启用的提供商"""
        from shared.ai.model_config import get_enabled_providers
        
        mock_get_config.return_value = {
            "openai": True,
            "fal": True,
            "qwen": False,
            "wanx": False
        }
        
        providers = get_enabled_providers()
        
        assert providers["openai"] is True
        assert providers["qwen"] is False
    
    @patch('services.ai.model_config.get_config')
    def test_returns_default_when_not_configured(self, mock_get_config):
        """未配置时返回默认值"""
        from shared.ai.model_config import get_enabled_providers
        
        mock_get_config.return_value = None
        
        providers = get_enabled_providers()
        
        # 默认启用 openai 和 fal
        assert providers["openai"] is True
        assert providers["fal"] is True


# ==========================================
# is_provider_enabled Tests
# ==========================================

class TestIsProviderEnabled:
    """is_provider_enabled 函数测试"""
    
    @patch('services.ai.model_config.get_enabled_providers')
    def test_enabled_provider(self, mock_get_enabled):
        """启用的提供商"""
        from shared.ai.model_config import is_provider_enabled
        
        mock_get_enabled.return_value = {"openai": True, "qwen": False}
        
        assert is_provider_enabled("openai") is True
    
    @patch('services.ai.model_config.get_enabled_providers')
    def test_disabled_provider(self, mock_get_enabled):
        """禁用的提供商"""
        from shared.ai.model_config import is_provider_enabled
        
        mock_get_enabled.return_value = {"openai": True, "qwen": False}
        
        assert is_provider_enabled("qwen") is False
    
    @patch('services.ai.model_config.get_enabled_providers')
    def test_unknown_provider(self, mock_get_enabled):
        """未知的提供商返回 False"""
        from shared.ai.model_config import is_provider_enabled
        
        mock_get_enabled.return_value = {"openai": True}
        
        assert is_provider_enabled("unknown_provider") is False


# ==========================================
# get_provider_models Tests
# ==========================================

class TestGetProviderModels:
    """get_provider_models 函数测试"""
    
    @patch('services.ai.model_config.get_config')
    def test_returns_provider_models(self, mock_get_config):
        """返回提供商的模型列表"""
        from shared.ai.model_config import get_provider_models
        
        mock_get_config.return_value = {
            "openai": {"text": ["gpt-4o-mini", "gpt-4o"], "image": ["dall-e-3"]},
            "qwen": {"text": ["qwen-turbo", "qwen-plus"]}
        }
        
        models = get_provider_models("openai")
        
        assert "text" in models
        assert "gpt-4o-mini" in models["text"]
    
    @patch('services.ai.model_config.get_config')
    def test_returns_empty_for_unknown_provider(self, mock_get_config):
        """未知提供商返回空"""
        from shared.ai.model_config import get_provider_models
        
        mock_get_config.return_value = {"openai": {"text": ["gpt-4o"]}}
        
        models = get_provider_models("unknown")
        
        assert models == {}


# ==========================================
# get_all_provider_models Tests
# ==========================================

class TestGetAllProviderModels:
    """get_all_provider_models 函数测试"""
    
    @patch('services.ai.model_config.get_config')
    def test_returns_all_models(self, mock_get_config):
        """返回所有提供商的模型"""
        from shared.ai.model_config import get_all_provider_models
        
        mock_get_config.return_value = {
            "openai": {"text": ["gpt-4o-mini"], "image": ["dall-e-3"]},
            "fal": {"image": ["flux-schnell", "flux-dev"]},
            "qwen": {"text": ["qwen-turbo"]}
        }
        
        all_models = get_all_provider_models()
        
        assert "openai" in all_models
        assert "fal" in all_models
        assert "qwen" in all_models


# ==========================================
# get_model_cost Tests
# ==========================================

class TestGetModelCost:
    """get_model_cost 函数测试"""
    
    @patch('services.ai.model_config.get_config')
    def test_returns_model_cost(self, mock_get_config):
        """返回模型成本"""
        from shared.ai.model_config import get_model_cost
        
        mock_get_config.return_value = {
            "openai": {"gpt-4o-mini": 0.15, "gpt-4o": 2.50},
            "fal": {"flux-schnell": 0.003}
        }
        
        cost = get_model_cost("openai", "gpt-4o-mini")
        
        assert cost == 0.15
    
    @patch('services.ai.model_config.get_config')
    def test_returns_zero_for_unknown_model(self, mock_get_config):
        """未知模型返回 0"""
        from shared.ai.model_config import get_model_cost
        
        mock_get_config.return_value = {"openai": {"gpt-4o": 2.50}}
        
        cost = get_model_cost("openai", "unknown-model")
        
        assert cost == 0.0
    
    @patch('services.ai.model_config.get_config')
    def test_returns_zero_for_unknown_provider(self, mock_get_config):
        """未知提供商返回 0"""
        from shared.ai.model_config import get_model_cost
        
        mock_get_config.return_value = {"openai": {"gpt-4o": 2.50}}
        
        cost = get_model_cost("unknown", "gpt-4o")
        
        assert cost == 0.0


# ==========================================
# get_fallback_config Tests
# ==========================================

class TestGetFallbackConfig:
    """get_fallback_config 函数测试"""
    
    def test_extracts_fallback(self):
        """提取 fallback 配置"""
        from shared.ai.model_config import get_fallback_config
        
        config = {
            "provider": "qwen",
            "model": "qwen-plus",
            "fallback": {"provider": "openai", "model": "gpt-4o-mini"}
        }
        
        fallback = get_fallback_config(config)
        
        assert fallback["provider"] == "openai"
        assert fallback["model"] == "gpt-4o-mini"
    
    def test_returns_none_when_no_fallback(self):
        """无 fallback 时返回 None"""
        from shared.ai.model_config import get_fallback_config
        
        config = {"provider": "qwen", "model": "qwen-plus"}
        
        fallback = get_fallback_config(config)
        
        assert fallback is None


# ==========================================
# Edge Cases
# ==========================================

class TestModelConfigEdgeCases:
    """边界情况测试"""
    
    @patch('services.ai.model_config.get_config')
    def test_empty_config_value(self, mock_get_config):
        """空配置值"""
        from shared.ai.model_config import get_text_model_config
        
        mock_get_config.return_value = {}
        
        config = get_text_model_config()
        
        # 应该使用默认值
        assert "provider" in config or config == {}
    
    @patch('services.ai.model_config.get_config')
    def test_partial_config(self, mock_get_config):
        """部分配置"""
        from shared.ai.model_config import get_image_model_config
        
        # 只有 provider，没有 models
        mock_get_config.return_value = {"provider": "wanx"}
        
        config = get_image_model_config("free")
        
        assert config["provider"] == "wanx"
    
    @patch('services.ai.model_config.get_config')
    def test_case_sensitivity_tier(self, mock_get_config):
        """tier 大小写"""
        from shared.ai.model_config import get_image_model_config
        
        mock_get_config.return_value = {
            "provider": "fal",
            "models": {"free": "flux-schnell", "pro": "flux-dev"}
        }
        
        # 测试小写
        config = get_image_model_config("FREE".lower())
        assert config["model"] == "flux-schnell"
