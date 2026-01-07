"""
AI Service Providers - Concrete implementations of AI interfaces.

This module re-exports existing AI adapters from services/ai/adapters
to make them available through the shared layer.

Note: We don't need to create new wrapper classes because the existing
adapters (FALImageAdapter, OpenAIAdapter, QwenAdapter) already implement
the correct interfaces (BaseImageAdapter, BaseTextAdapter) which match
our new IImageAIService and ITextAIService interfaces.

@module shared.ai.providers
@version 1.0.0
"""

# Re-export existing adapters as providers
from services.ai.adapters.fal_adapter import FALImageAdapter as FalImageProvider
from services.ai.adapters.openai_adapter import OpenAITextAdapter as OpenAITextProvider
from services.ai.adapters.openai_adapter import OpenAIImageAdapter as OpenAIImageProvider
from services.ai.adapters.qwen_adapter import QwenTextAdapter as QwenTextProvider
from services.ai.adapters.qwen_adapter import WanxImageAdapter as WanxImageProvider

__all__ = [
    # Image AI Providers
    "FalImageProvider",
    "OpenAIImageProvider",
    "WanxImageProvider",
    # Text AI Providers
    "OpenAITextProvider",
    "QwenTextProvider",
]
