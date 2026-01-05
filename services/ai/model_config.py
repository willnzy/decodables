"""
AI Model Configuration Service
AI 模型配置服务

Provides centralized access to AI model configurations
stored in system_configs table.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..config_service import get_config

logger = logging.getLogger(__name__)


# ==========================================
# Default Configurations (Fallbacks)
# ==========================================

DEFAULT_TEXT_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "fallback": {"provider": "openai", "model": "gpt-4o-mini"},
    "show_provider": False,
}

DEFAULT_IMAGE_CONFIG = {
    "provider": "fal",
    "models": {
        "free": "flux-schnell",
        "starter": "flux-schnell",
        "pro": "flux-dev",
    },
    "fallback": {"provider": "fal", "model": "flux-schnell"},
    "show_provider": False,
}

DEFAULT_ADMIN_CONFIG = {
    "provider": "openai",
    "model": "gpt-4o",
    "fallback": {"provider": "openai", "model": "gpt-4o-mini"},
}

DEFAULT_ENABLED_PROVIDERS = {
    "openai": True,
    "fal": True,
    "qwen": False,
    "gemini": False,
    "grok": False,
    "jimeng": False,
    "anthropic": False,
}


# ==========================================
# Data Classes
# ==========================================

@dataclass
class ModelConfig:
    """Model configuration"""
    provider: str
    model: str
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    show_provider: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "fallback": {
                "provider": self.fallback_provider,
                "model": self.fallback_model,
            } if self.fallback_provider else None,
            "show_provider": self.show_provider,
        }


# ==========================================
# Configuration Getters
# ==========================================

def get_text_model_config() -> ModelConfig:
    """
    Get user text reasoning model configuration.
    
    Returns:
        ModelConfig for text/chat operations
    """
    config = get_config("ai_model.user.text_reasoning") or DEFAULT_TEXT_CONFIG
    
    fallback = config.get("fallback", {})
    
    return ModelConfig(
        provider=config.get("provider", "openai"),
        model=config.get("model", "gpt-4o-mini"),
        fallback_provider=fallback.get("provider"),
        fallback_model=fallback.get("model"),
        show_provider=config.get("show_provider", False),
    )


def get_image_model_config(tier: str = "free") -> ModelConfig:
    """
    Get user image generation model configuration.
    
    Args:
        tier: User tier ("free", "starter", "pro")
        
    Returns:
        ModelConfig for image generation
    """
    config = get_config("ai_model.user.image_generation") or DEFAULT_IMAGE_CONFIG
    
    # Get model based on tier
    models = config.get("models", {})
    model = models.get(tier, models.get("free", "flux-schnell"))
    
    fallback = config.get("fallback", {})
    
    return ModelConfig(
        provider=config.get("provider", "fal"),
        model=model,
        fallback_provider=fallback.get("provider"),
        fallback_model=fallback.get("model"),
        show_provider=config.get("show_provider", False),
    )


def get_admin_model_config() -> ModelConfig:
    """
    Get admin analysis model configuration.
    
    Returns:
        ModelConfig for admin AI analysis
    """
    config = get_config("ai_model.admin.analysis") or DEFAULT_ADMIN_CONFIG
    
    fallback = config.get("fallback", {})
    
    return ModelConfig(
        provider=config.get("provider", "openai"),
        model=config.get("model", "gpt-4o"),
        fallback_provider=fallback.get("provider"),
        fallback_model=fallback.get("model"),
    )


def get_enabled_providers() -> Dict[str, bool]:
    """
    Get enabled/disabled status of all providers.
    
    Returns:
        Dict of provider -> is_enabled
    """
    return get_config("ai_providers.enabled") or DEFAULT_ENABLED_PROVIDERS


def is_provider_enabled(provider: str) -> bool:
    """
    Check if a specific provider is enabled.
    
    Args:
        provider: Provider name
        
    Returns:
        True if enabled
    """
    providers = get_enabled_providers()
    return providers.get(provider, False)


def get_provider_models(provider: str) -> Dict[str, List[str]]:
    """
    Get available models for a provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Dict with "text" and/or "image" model lists
    """
    all_models = get_config("ai_providers.models") or {}
    return all_models.get(provider, {})


def get_all_provider_models() -> Dict[str, Dict[str, List[str]]]:
    """
    Get all provider models configuration.
    
    Returns:
        Dict of provider -> {"text": [...], "image": [...]}
    """
    return get_config("ai_providers.models") or {}


def get_provider_timeout(provider: str, call_type: str = "text") -> int:
    """
    Get timeout configuration for a provider.
    
    Args:
        provider: Provider name
        call_type: "text" or "image"
        
    Returns:
        Timeout in seconds
    """
    timeouts = get_config("ai_providers.timeouts") or {}
    provider_timeouts = timeouts.get(provider, {})
    
    if isinstance(provider_timeouts, dict):
        return provider_timeouts.get(call_type, 60)
    return provider_timeouts if isinstance(provider_timeouts, int) else 60


def get_model_cost(provider: str, model: str) -> float:
    """
    Get estimated cost for a model.
    
    Args:
        provider: Provider name
        model: Model name
        
    Returns:
        Cost per 1M tokens or per image (USD)
    """
    costs = get_config("ai_providers.costs") or {}
    provider_costs = costs.get(provider, {})
    return provider_costs.get(model, 0.0)


# ==========================================
# Configuration Setters (Admin only)
# ==========================================

def update_text_model_config(
    provider: str,
    model: str,
    fallback_provider: str = None,
    fallback_model: str = None,
    show_provider: bool = False,
    updated_by: str = None
) -> bool:
    """
    Update user text model configuration.
    
    Returns:
        True if successful
    """
    from ..config_service import set_config
    
    config = {
        "provider": provider,
        "model": model,
        "show_provider": show_provider,
    }
    
    if fallback_provider and fallback_model:
        config["fallback"] = {
            "provider": fallback_provider,
            "model": fallback_model,
        }
    
    return set_config("ai_model.user.text_reasoning", config, updated_by)


def update_image_model_config(
    provider: str,
    models: Dict[str, str],
    fallback_provider: str = None,
    fallback_model: str = None,
    show_provider: bool = False,
    updated_by: str = None
) -> bool:
    """
    Update user image model configuration.
    
    Args:
        models: Dict of tier -> model name
        
    Returns:
        True if successful
    """
    from ..config_service import set_config
    
    config = {
        "provider": provider,
        "models": models,
        "show_provider": show_provider,
    }
    
    if fallback_provider and fallback_model:
        config["fallback"] = {
            "provider": fallback_provider,
            "model": fallback_model,
        }
    
    return set_config("ai_model.user.image_generation", config, updated_by)


def update_admin_model_config(
    provider: str,
    model: str,
    fallback_provider: str = None,
    fallback_model: str = None,
    updated_by: str = None
) -> bool:
    """
    Update admin analysis model configuration.
    
    Returns:
        True if successful
    """
    from ..config_service import set_config
    
    config = {
        "provider": provider,
        "model": model,
    }
    
    if fallback_provider and fallback_model:
        config["fallback"] = {
            "provider": fallback_provider,
            "model": fallback_model,
        }
    
    return set_config("ai_model.admin.analysis", config, updated_by)


def update_provider_status(provider: str, enabled: bool, updated_by: str = None) -> bool:
    """
    Enable or disable a provider.
    
    Returns:
        True if successful
    """
    from ..config_service import set_config
    
    providers = get_enabled_providers()
    providers[provider] = enabled
    
    return set_config("ai_providers.enabled", providers, updated_by)


# ==========================================
# Validation
# ==========================================

def validate_model_config(provider: str, model: str, call_type: str = "text") -> bool:
    """
    Validate that a provider/model combination is valid and enabled.
    
    Args:
        provider: Provider name
        model: Model name
        call_type: "text" or "image"
        
    Returns:
        True if valid
    """
    # Check provider is enabled
    if not is_provider_enabled(provider):
        logger.warning(f"[ModelConfig] Provider not enabled: {provider}")
        return False
    
    # Check model exists
    provider_models = get_provider_models(provider)
    available_models = provider_models.get(call_type, [])
    
    if model not in available_models:
        logger.warning(f"[ModelConfig] Model not found: {provider}/{model}")
        return False
    
    return True
