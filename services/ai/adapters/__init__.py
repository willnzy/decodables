"""
AI Provider Adapters
AI 提供商适配器

Registry and factory for AI provider adapters.
"""

from typing import Dict, Optional
import logging

from ..base import (
    BaseTextAdapter,
    BaseImageAdapter,
    AIProviderType,
    AIAdapterError,
)

logger = logging.getLogger(__name__)

# Adapter registries
_text_adapters: Dict[str, BaseTextAdapter] = {}
_image_adapters: Dict[str, BaseImageAdapter] = {}


def register_text_adapter(provider: str, adapter: BaseTextAdapter):
    """Register a text adapter for a provider."""
    _text_adapters[provider] = adapter
    logger.info(f"[AIAdapters] Registered text adapter: {provider}")


def register_image_adapter(provider: str, adapter: BaseImageAdapter):
    """Register an image adapter for a provider."""
    _image_adapters[provider] = adapter
    logger.info(f"[AIAdapters] Registered image adapter: {provider}")


def get_text_adapter(provider: str) -> BaseTextAdapter:
    """
    Get text adapter for a provider.
    
    Args:
        provider: Provider name (e.g., "openai", "qwen")
        
    Returns:
        Text adapter instance
        
    Raises:
        AIAdapterError: If adapter not found or not available
    """
    adapter = _text_adapters.get(provider)
    
    if not adapter:
        raise AIAdapterError(
            f"Text adapter not found for provider: {provider}",
            provider=provider
        )
    
    if not adapter.is_available():
        raise AIAdapterError(
            f"Text adapter not available (check API key): {provider}",
            provider=provider
        )
    
    return adapter


def get_image_adapter(provider: str) -> BaseImageAdapter:
    """
    Get image adapter for a provider.
    
    Args:
        provider: Provider name (e.g., "fal", "openai")
        
    Returns:
        Image adapter instance
        
    Raises:
        AIAdapterError: If adapter not found or not available
    """
    adapter = _image_adapters.get(provider)
    
    if not adapter:
        raise AIAdapterError(
            f"Image adapter not found for provider: {provider}",
            provider=provider
        )
    
    if not adapter.is_available():
        raise AIAdapterError(
            f"Image adapter not available (check API key): {provider}",
            provider=provider
        )
    
    return adapter


def list_available_text_adapters() -> Dict[str, bool]:
    """
    List all text adapters and their availability.
    
    Returns:
        Dict of provider -> is_available
    """
    return {
        provider: adapter.is_available()
        for provider, adapter in _text_adapters.items()
    }


def list_available_image_adapters() -> Dict[str, bool]:
    """
    List all image adapters and their availability.
    
    Returns:
        Dict of provider -> is_available
    """
    return {
        provider: adapter.is_available()
        for provider, adapter in _image_adapters.items()
    }


# ==========================================
# Auto-register adapters on import
# ==========================================

def _init_adapters():
    """Initialize and register all available adapters."""
    
    # OpenAI
    try:
        from .openai_adapter import OpenAITextAdapter, OpenAIImageAdapter
        register_text_adapter("openai", OpenAITextAdapter())
        register_image_adapter("openai", OpenAIImageAdapter())
    except ImportError as e:
        logger.warning(f"[AIAdapters] OpenAI adapter not available: {e}")
    
    # FAL
    try:
        from .fal_adapter import FALImageAdapter
        register_image_adapter("fal", FALImageAdapter())
    except ImportError as e:
        logger.warning(f"[AIAdapters] FAL adapter not available: {e}")
    
    # Anthropic (Claude)
    try:
        from .anthropic_adapter import AnthropicTextAdapter
        register_text_adapter("anthropic", AnthropicTextAdapter())
    except ImportError as e:
        logger.debug(f"[AIAdapters] Anthropic adapter not available: {e}")
    
    # Qwen (通义千问)
    try:
        from .qwen_adapter import QwenTextAdapter
        register_text_adapter("qwen", QwenTextAdapter())
    except ImportError as e:
        logger.debug(f"[AIAdapters] Qwen adapter not available: {e}")
    
    # Gemini
    try:
        from .gemini_adapter import GeminiTextAdapter
        register_text_adapter("gemini", GeminiTextAdapter())
    except ImportError as e:
        logger.debug(f"[AIAdapters] Gemini adapter not available: {e}")
    
    logger.info(
        f"[AIAdapters] Initialized - Text: {list(_text_adapters.keys())}, "
        f"Image: {list(_image_adapters.keys())}"
    )


# Initialize on module load
_init_adapters()


__all__ = [
    "get_text_adapter",
    "get_image_adapter",
    "list_available_text_adapters",
    "list_available_image_adapters",
    "register_text_adapter",
    "register_image_adapter",
]
