"""
AI Services Package
AI 服务模块

包含:
- 统一 AI 服务 (文本/图像)
- 模型配置管理
- 灰度发布
- 使用量追踪
- 适配器 (OpenAI, FAL, etc.)

原有服务 (向后兼容):
- image_generator: FAL 图像生成
- story_generator: 故事 JSON 生成
- prompt_enhancer: 提示词增强
- zine_generator: 可折叠书生成
"""

# ==========================================
# Legacy Exports (向后兼容)
# ==========================================

from .image_generator import generate_8_images
from .story_generator import generate_story_json
from .zine_generator import create_foldable_book, create_assets_zip
from .prompt_enhancer import enhance_prompt, enhance_asset_prompt

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
    # Legacy
    'generate_8_images',
    'generate_story_json',
    'create_foldable_book',
    'create_assets_zip',
    'enhance_prompt',
    'enhance_asset_prompt',
    
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
