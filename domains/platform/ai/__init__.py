"""
AI 模块 - AI 模型配置管理

@module domains.platform.ai
@version 3.30 (DDD Migration)

This domain handles:
- AI model configuration management (CRUD)
- Provider management
- Canary rollout configuration
- Cache management
- Usage statistics
"""

from domains.platform.ai.service import (
    # Configuration (读)
    get_model_configs,
    # Configuration (写)
    update_text_model_config,
    update_image_model_config,
    update_canary_config,
    toggle_ai_provider,
    # Usage
    get_ai_usage_stats,
    # Cache
    clear_ai_cache,
)

__all__ = [
    "get_model_configs",
    "update_text_model_config",
    "update_image_model_config",
    "update_canary_config",
    "toggle_ai_provider",
    "get_ai_usage_stats",
    "clear_ai_cache",
]
