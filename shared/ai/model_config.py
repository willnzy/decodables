"""
AI Model Configuration Service
AI 模型配置服务

Provides:
- Get model configuration from system_configs
- Support for user text/image models
- Support for admin analysis model
- Provider availability checking
"""

import logging
from typing import Dict, Any, Optional, List

from ..config_service import get_config

logger = logging.getLogger(__name__)


# ==========================================
# Default Configurations (Fallback)
# ==========================================

DEFAULT_TEXT_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "fallback": {"provider": "openai", "model": "gpt-4o-mini"},
    "show_provider": False
}

DEFAULT_IMAGE_CONFIG = {
    "provider": "fal",
    "models": {
        "free": "flux-schnell",
        "starter": "flux-schnell", 
        "pro": "flux-dev"
    },
    "fallback": {"provider": "fal", "model": "flux-schnell"},
    "show_provider": False
}

DEFAULT_ADMIN_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o",
    "fallback": {"provider": "openai", "model": "gpt-4o-mini"}
}

DEFAULT_ENABLED_PROVIDERS = {
    "openai": True,
    "fal": True,
    "qwen": False,
    "gemini": False,
    "grok": False,
    "jimeng": False,
    "anthropic": False
}


# ==========================================
# Configuration Getters
# ==========================================

def get_text_model_config() -> Dict[str, Any]:
    """
    获取用户文本推理模型配置
    
    Returns:
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "fallback": {"provider": "openai", "model": "gpt-4o-mini"},
            "show_provider": False
        }
    """
    config = get_config("ai_model.user.text_reasoning")
    if not config:
        logger.debug("[ModelConfig] Using default text model config")
        return DEFAULT_TEXT_CONFIG.copy()
    return config


def get_image_model_config(tier: str = "free") -> Dict[str, Any]:
    """
    获取用户图像生成模型配置
    
    Args:
        tier: 用户等级 (free, starter, pro)
        
    Returns:
        {
            "provider": "fal",
            "model": "flux-schnell",  # 根据 tier 选择
            "fallback": {"provider": "fal", "model": "flux-schnell"},
            "show_provider": False
        }
    """
    config = get_config("ai_model.user.image_generation")
    if not config:
        logger.debug("[ModelConfig] Using default image model config")
        config = DEFAULT_IMAGE_CONFIG.copy()
    
    # 根据 tier 选择具体模型
    models = config.get("models", DEFAULT_IMAGE_CONFIG["models"])
    model = models.get(tier, models.get("free", "flux-schnell"))
    
    return {
        "provider": config.get("provider", "fal"),
        "model": model,
        "fallback": config.get("fallback", DEFAULT_IMAGE_CONFIG["fallback"]),
        "show_provider": config.get("show_provider", False)
    }


def get_admin_model_config() -> Dict[str, Any]:
    """
    获取 Admin 分析模型配置
    
    Returns:
        {
            "provider": "openai",
            "model": "gpt-4o",
            "fallback": {"provider": "openai", "model": "gpt-4o-mini"}
        }
    """
    config = get_config("ai_model.admin.analysis")
    if not config:
        logger.debug("[ModelConfig] Using default admin model config")
        return DEFAULT_ADMIN_CONFIG.copy()
    return config


def get_enabled_providers() -> Dict[str, bool]:
    """
    获取已启用的 AI 提供商
    
    Returns:
        {"openai": True, "fal": True, "qwen": False, ...}
    """
    config = get_config("ai_providers.enabled")
    if not config:
        return DEFAULT_ENABLED_PROVIDERS.copy()
    return config


def get_provider_models(provider: str) -> Dict[str, List[str]]:
    """
    获取指定提供商的可用模型列表
    
    Args:
        provider: 提供商名称
        
    Returns:
        {"text": ["gpt-4o-mini", "gpt-4o"], "image": ["dall-e-3"]}
    """
    all_models = get_config("ai_providers.models") or {}
    return all_models.get(provider, {})


def get_all_provider_models() -> Dict[str, Dict[str, List[str]]]:
    """
    获取所有提供商的模型列表
    
    Returns:
        {
            "openai": {"text": [...], "image": [...]},
            "fal": {"image": [...]},
            ...
        }
    """
    return get_config("ai_providers.models") or {}


def get_provider_timeout(provider: str, call_type: str = "text") -> int:
    """
    获取提供商超时配置
    
    Args:
        provider: 提供商名称
        call_type: 调用类型 (text, image)
        
    Returns:
        超时秒数
    """
    timeouts = get_config("ai_providers.timeouts") or {}
    provider_timeouts = timeouts.get(provider, {})
    
    # 默认超时
    default_timeout = 60 if call_type == "text" else 180
    return provider_timeouts.get(call_type, default_timeout)


def get_model_cost(provider: str, model: str) -> float:
    """
    获取模型成本参考值
    
    Args:
        provider: 提供商名称
        model: 模型名称
        
    Returns:
        成本 (USD per 1M tokens 或 per image)
    """
    costs = get_config("ai_providers.costs") or {}
    provider_costs = costs.get(provider, {})
    return provider_costs.get(model, 0.0)


def get_retry_config() -> Dict[str, Any]:
    """
    获取重试配置
    
    Returns:
        {
            "max_retries": 3,
            "base_delay_ms": 1000,
            "max_delay_ms": 10000,
            "retry_on_status": [429, 500, 502, 503, 504]
        }
    """
    return get_config("ai_providers.retry") or {
        "max_retries": 3,
        "base_delay_ms": 1000,
        "max_delay_ms": 10000,
        "retry_on_status": [429, 500, 502, 503, 504]
    }


# ==========================================
# Utility Functions
# ==========================================

def is_provider_enabled(provider: str) -> bool:
    """检查提供商是否启用"""
    enabled = get_enabled_providers()
    return enabled.get(provider, False)


def get_fallback_config(config: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """从配置中提取 fallback 配置"""
    return config.get("fallback")


def should_show_provider(config: Dict[str, Any]) -> bool:
    """检查是否应该向用户显示提供商信息"""
    return config.get("show_provider", False)
