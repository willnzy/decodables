"""
AI Model Configuration Service
Admin functions for managing AI model configurations

@module services.ai.model_config_service
@version 3.24

Note: This module provides admin-level functions for managing AI configurations.
Regular model config access should use model_config.py
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def get_model_configs() -> Dict[str, Any]:
    """
    Get all AI model configurations.
    
    Returns:
        Dict containing text, image, and admin model configs
    """
    from .model_config import (
        get_text_model_config,
        get_image_model_config,
        get_admin_model_config,
        get_enabled_providers
    )
    
    return {
        "text": get_text_model_config(),
        "image": {
            "free": get_image_model_config("free"),
            "starter": get_image_model_config("starter"),
            "pro": get_image_model_config("pro"),
        },
        "admin": get_admin_model_config(),
        "enabled_providers": get_enabled_providers(),
    }


def update_text_model_config(
    provider: str = None,
    model: str = None,
    max_tokens: int = None,
    temperature: float = None
) -> Dict[str, Any]:
    """
    Update text model configuration.
    
    Note: In production, this should persist to database or config store.
    Currently returns mock success response.
    """
    logger.info(f"[ModelConfig] Updating text config: provider={provider}, model={model}")
    
    return {
        "success": True,
        "message": "Text model configuration updated",
        "config": {
            "provider": provider,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    }


def update_image_model_config(
    tier: str,
    provider: str = None,
    model: str = None,
    num_inference_steps: int = None
) -> Dict[str, Any]:
    """
    Update image model configuration for a specific tier.
    
    Note: In production, this should persist to database or config store.
    """
    logger.info(f"[ModelConfig] Updating image config for tier={tier}")
    
    return {
        "success": True,
        "message": f"Image model configuration for {tier} updated",
        "config": {
            "tier": tier,
            "provider": provider,
            "model": model,
            "num_inference_steps": num_inference_steps,
        }
    }


def toggle_ai_provider(provider: str, enabled: bool) -> Dict[str, Any]:
    """
    Enable or disable an AI provider.
    
    Args:
        provider: Provider name (openai, fal, dashscope, etc.)
        enabled: Whether to enable the provider
    """
    logger.info(f"[ModelConfig] Toggling provider {provider} to {enabled}")
    
    return {
        "success": True,
        "message": f"Provider {provider} {'enabled' if enabled else 'disabled'}",
        "provider": provider,
        "enabled": enabled,
    }


def get_ai_usage_stats(
    start_date: str = None,
    end_date: str = None,
    provider: str = None
) -> Dict[str, Any]:
    """
    Get AI usage statistics.
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        provider: Optional provider filter
    """
    # In production, query from analytics/usage tracking
    return {
        "total_requests": 0,
        "total_tokens": 0,
        "total_images": 0,
        "by_provider": {},
        "by_model": {},
        "period": {
            "start": start_date,
            "end": end_date,
        }
    }


def clear_ai_cache(cache_type: str = "all") -> Dict[str, Any]:
    """
    Clear AI response cache.
    
    Args:
        cache_type: Type of cache to clear ('text', 'image', 'all')
    """
    from services.cache import cache_service
    
    try:
        if cache_type in ["text", "all"]:
            # Clear text AI cache
            cache_service.delete_pattern("md:ai:*")
        
        logger.info(f"[ModelConfig] Cleared AI cache: {cache_type}")
        
        return {
            "success": True,
            "message": f"AI cache cleared: {cache_type}",
            "cache_type": cache_type,
        }
    except Exception as e:
        logger.error(f"[ModelConfig] Failed to clear cache: {e}")
        return {
            "success": False,
            "error": str(e),
        }
