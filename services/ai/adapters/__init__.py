"""
AI Provider Adapters Factory
AI 提供商适配器工厂

Provides:
- Adapter registration and lookup
- Factory functions for text and image adapters
- Lazy loading to avoid import errors when API keys are missing
"""

import logging
from typing import Dict, Optional, Type

from ..base import BaseTextAdapter, BaseImageAdapter

logger = logging.getLogger(__name__)

# ==========================================
# Adapter Registry
# ==========================================

# Text adapter registry: provider_name -> adapter_class
_text_adapters: Dict[str, Type[BaseTextAdapter]] = {}

# Image adapter registry: provider_name -> adapter_class  
_image_adapters: Dict[str, Type[BaseImageAdapter]] = {}

# Singleton instances (lazy loaded)
_text_adapter_instances: Dict[str, BaseTextAdapter] = {}
_image_adapter_instances: Dict[str, BaseImageAdapter] = {}


def register_text_adapter(provider: str, adapter_class: Type[BaseTextAdapter]):
    """注册文本适配器"""
    _text_adapters[provider] = adapter_class
    logger.debug(f"[AI Adapters] Registered text adapter: {provider}")


def register_image_adapter(provider: str, adapter_class: Type[BaseImageAdapter]):
    """注册图像适配器"""
    _image_adapters[provider] = adapter_class
    logger.debug(f"[AI Adapters] Registered image adapter: {provider}")


# ==========================================
# Factory Functions
# ==========================================

def get_text_adapter(provider: str) -> Optional[BaseTextAdapter]:
    """
    获取文本适配器实例
    
    Args:
        provider: 提供商名称 (openai, qwen, gemini, anthropic, grok)
        
    Returns:
        适配器实例，如果提供商不可用则返回 None
    """
    # 懒加载适配器
    if provider not in _text_adapter_instances:
        adapter_class = _text_adapters.get(provider)
        if not adapter_class:
            logger.warning(f"[AI Adapters] Text adapter not found: {provider}")
            return None
        
        try:
            instance = adapter_class()
            if instance.is_available():
                _text_adapter_instances[provider] = instance
            else:
                logger.warning(f"[AI Adapters] Text adapter not available (missing API key?): {provider}")
                return None
        except Exception as e:
            logger.error(f"[AI Adapters] Failed to initialize text adapter {provider}: {e}")
            return None
    
    return _text_adapter_instances.get(provider)


def get_image_adapter(provider: str) -> Optional[BaseImageAdapter]:
    """
    获取图像适配器实例
    
    Args:
        provider: 提供商名称 (fal, openai, qwen, jimeng)
        
    Returns:
        适配器实例，如果提供商不可用则返回 None
    """
    # 懒加载适配器
    if provider not in _image_adapter_instances:
        adapter_class = _image_adapters.get(provider)
        if not adapter_class:
            logger.warning(f"[AI Adapters] Image adapter not found: {provider}")
            return None
        
        try:
            instance = adapter_class()
            if instance.is_available():
                _image_adapter_instances[provider] = instance
            else:
                logger.warning(f"[AI Adapters] Image adapter not available (missing API key?): {provider}")
                return None
        except Exception as e:
            logger.error(f"[AI Adapters] Failed to initialize image adapter {provider}: {e}")
            return None
    
    return _image_adapter_instances.get(provider)


def get_available_text_providers() -> list:
    """获取所有已注册且可用的文本提供商"""
    available = []
    for provider in _text_adapters.keys():
        adapter = get_text_adapter(provider)
        if adapter and adapter.is_available():
            available.append(provider)
    return available


def get_available_image_providers() -> list:
    """获取所有已注册且可用的图像提供商"""
    available = []
    for provider in _image_adapters.keys():
        adapter = get_image_adapter(provider)
        if adapter and adapter.is_available():
            available.append(provider)
    return available


def clear_adapter_cache():
    """清除适配器实例缓存 (用于测试或重新加载配置)"""
    global _text_adapter_instances, _image_adapter_instances
    _text_adapter_instances.clear()
    _image_adapter_instances.clear()
    logger.info("[AI Adapters] Adapter cache cleared")


# ==========================================
# Auto-register adapters on import
# ==========================================

def _auto_register_adapters():
    """自动注册所有可用的适配器"""
    # OpenAI
    try:
        from .openai_adapter import OpenAITextAdapter, OpenAIImageAdapter
        register_text_adapter("openai", OpenAITextAdapter)
        register_image_adapter("openai", OpenAIImageAdapter)
    except ImportError as e:
        logger.debug(f"[AI Adapters] OpenAI adapter not available: {e}")
    
    # FAL
    try:
        from .fal_adapter import FALImageAdapter
        register_image_adapter("fal", FALImageAdapter)
    except ImportError as e:
        logger.debug(f"[AI Adapters] FAL adapter not available: {e}")
    
    # Qwen (Alibaba)
    try:
        from .qwen_adapter import QwenTextAdapter, QwenImageAdapter
        register_text_adapter("qwen", QwenTextAdapter)
        register_image_adapter("qwen", QwenImageAdapter)
    except ImportError as e:
        logger.debug(f"[AI Adapters] Qwen adapter not available: {e}")
    
    # Gemini (Google)
    try:
        from .gemini_adapter import GeminiTextAdapter
        register_text_adapter("gemini", GeminiTextAdapter)
    except ImportError as e:
        logger.debug(f"[AI Adapters] Gemini adapter not available: {e}")
    
    # Anthropic (Claude)
    try:
        from .anthropic_adapter import AnthropicTextAdapter
        register_text_adapter("anthropic", AnthropicTextAdapter)
    except ImportError as e:
        logger.debug(f"[AI Adapters] Anthropic adapter not available: {e}")
    
    # Grok (xAI)
    try:
        from .grok_adapter import GrokTextAdapter
        register_text_adapter("grok", GrokTextAdapter)
    except ImportError as e:
        logger.debug(f"[AI Adapters] Grok adapter not available: {e}")
    
    # Jimeng (ByteDance)
    try:
        from .jimeng_adapter import JimengImageAdapter
        register_image_adapter("jimeng", JimengImageAdapter)
    except ImportError as e:
        logger.debug(f"[AI Adapters] Jimeng adapter not available: {e}")


# Run auto-registration
_auto_register_adapters()


# ==========================================
# Exports
# ==========================================

__all__ = [
    "get_text_adapter",
    "get_image_adapter",
    "get_available_text_providers",
    "get_available_image_providers",
    "register_text_adapter",
    "register_image_adapter",
    "clear_adapter_cache",
]
