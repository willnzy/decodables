"""
AI Services Package
AI 服务模块

包含:
- 统一 AI 服务 (文本/图像)
- 模型配置管理
- 灰度发布
- 使用量追踪
- 适配器 (OpenAI, FAL, Qwen, Wanx, etc.)

业务服务 (基于统一服务):
- image_generator: 图像生成 (多图、参考图、存储)
- story_generator: 故事 JSON 生成
- prompt_enhancer: 提示词增强
- zine_generator: 可折叠书生成
"""

# ==========================================
# Business Services (基于统一 AI 服务)
# ==========================================

from .image_generator import generate_8_images, generate_images_async
from .story_generator import generate_story_json, generate_story_json_async
from .zine_generator import create_foldable_book, create_assets_zip
from .prompt_enhancer import (
    enhance_prompt, 
    enhance_asset_prompt,
    enhance_prompt_async,
    enhance_asset_prompt_async,
)

# ==========================================
# New Unified Services (v3.21)
# ==========================================

# 基础类
from .base import (
    AIResponse,
    AIUsage,
    AIMessage,
    AICallType,
    AIErrorType,
    BaseTextAdapter,
    BaseImageAdapter,
)

# 统一服务
from .unified_text_service import (
    unified_text_service,
    chat,
    admin_chat,
)

from .unified_image_service import (
    unified_image_service,
    generate_image,
    image_to_image,
)

# 配置服务
from .model_config import (
    get_text_model_config,
    get_image_model_config,
    get_admin_model_config,
    get_enabled_providers,
    get_provider_models,
    get_all_provider_models,
    is_provider_enabled,
)

# 灰度发布
from .canary import (
    should_use_canary,
    get_canary_config,
    get_canary_status,
)

# 使用量追踪
from .usage_tracker import (
    track_ai_usage,
    track_ai_usage_sync,
    get_usage_summary,
    get_daily_trend,
)

# 缓存
from .ai_cache import (
    get_cached_result,
    set_cached_result,
    invalidate_ai_cache,
)

# 适配器工厂
from .adapters import (
    get_text_adapter,
    get_image_adapter,
    get_available_text_providers,
    get_available_image_providers,
)


# ==========================================
# All Exports
# ==========================================

__all__ = [
    # Business Services (基于统一 AI 服务)
    'generate_8_images',
    'generate_images_async',
    'generate_story_json',
    'generate_story_json_async',
    'create_foldable_book',
    'create_assets_zip',
    'enhance_prompt',
    'enhance_asset_prompt',
    'enhance_prompt_async',
    'enhance_asset_prompt_async',
    
    # Base classes
    'AIResponse',
    'AIUsage',
    'AIMessage',
    'AICallType',
    'AIErrorType',
    'BaseTextAdapter',
    'BaseImageAdapter',
    
    # Unified services
    'unified_text_service',
    'unified_image_service',
    'chat',
    'admin_chat',
    'generate_image',
    'image_to_image',
    
    # Config
    'get_text_model_config',
    'get_image_model_config',
    'get_admin_model_config',
    'get_enabled_providers',
    'get_provider_models',
    'get_all_provider_models',
    'is_provider_enabled',
    
    # Canary
    'should_use_canary',
    'get_canary_config',
    'get_canary_status',
    
    # Usage tracking
    'track_ai_usage',
    'track_ai_usage_sync',
    'get_usage_summary',
    'get_daily_trend',
    
    # Cache
    'get_cached_result',
    'set_cached_result',
    'invalidate_ai_cache',
    
    # Adapters
    'get_text_adapter',
    'get_image_adapter',
    'get_available_text_providers',
    'get_available_image_providers',
]
