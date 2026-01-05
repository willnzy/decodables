"""
AI Services Package
AI generation related modules

Provides:
- Legacy functions (generate_8_images, generate_story_json, etc.)
- Unified services (unified_text, unified_image)
- Adapters for multiple AI providers
- Model configuration and canary releases
"""

# Legacy exports (for backward compatibility)
from .image_generator import generate_8_images
from .story_generator import generate_story_json
from .zine_generator import create_foldable_book, create_assets_zip
from .prompt_enhancer import enhance_prompt, enhance_asset_prompt

# New unified services
from .unified_text_service import unified_text, chat
from .unified_image_service import unified_image, generate_image

# Model configuration
from .model_config import (
    get_text_model_config,
    get_image_model_config,
    get_admin_model_config,
    get_enabled_providers,
    is_provider_enabled,
)

# Canary release
from .canary import should_use_canary, get_canary_stats

# Usage tracking
from .usage_tracker import track_ai_usage, get_usage_summary

# Base classes (for type hints)
from .base import (
    TextCompletionResult,
    ImageGenerationResult,
    AIAdapterError,
)


__all__ = [
    # Legacy
    'generate_8_images',
    'generate_story_json',
    'create_foldable_book',
    'create_assets_zip',
    'enhance_prompt',
    'enhance_asset_prompt',
    
    # Unified services
    'unified_text',
    'unified_image',
    'chat',
    'generate_image',
    
    # Configuration
    'get_text_model_config',
    'get_image_model_config',
    'get_admin_model_config',
    'get_enabled_providers',
    'is_provider_enabled',
    
    # Canary
    'should_use_canary',
    'get_canary_stats',
    
    # Usage
    'track_ai_usage',
    'get_usage_summary',
    
    # Types
    'TextCompletionResult',
    'ImageGenerationResult',
    'AIAdapterError',
]
