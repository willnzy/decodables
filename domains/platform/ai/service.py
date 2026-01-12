"""
AI 模块 Domain Service - AI 模型配置业务逻辑

@module domains.platform.ai.service
@version 3.31 (Repository Dependency Injection)

Changes in v3.31:
- Added Repository dependency injection
- Added factory function for ConfigRepository
- All write functions now accept optional config_repo parameter
- Improved testability and SOLID compliance

Changes in v3.30:
- Complete DDD Migration from api/admin/ai_models.py (AIM-CRITICAL-1)
- All business logic moved to Service layer
- API layer only handles HTTP concerns
- Fixed Sync/Async混用 (AIM-CRITICAL-2) - 全部改为 async
- Canary 端点从 API 层迁移到 Service 层 (AIM-CRITICAL-3)
- 实现真实数据持久化 (AIM-HIGH-1)
- 添加 Audit Log (AIM-SEC-2)

Architecture:
- API → Service → ConfigService/Shared (for Config, with DI support)
- API → Service → CacheProvider (for Cache)
"""

import logging
import asyncio

from core.database import get_async_db_client
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from domains.platform.ai.constants import (
    CONFIG_KEY_TEXT_MODEL,
    CONFIG_KEY_IMAGE_MODEL,
    CONFIG_KEY_ADMIN_MODEL,
    CONFIG_KEY_ENABLED_PROVIDERS,
    CONFIG_KEY_CANARY,
    CACHE_PREFIX_TEXT,
    CACHE_PREFIX_IMAGE,
    CACHE_PREFIX_ALL,
    TIER_ALL,
)
from domains.platform.repository import IAIModelConfigRepository

logger = logging.getLogger(__name__)


# ==========================================
# Repository Factory Functions
# ==========================================

def _get_config_repo(repo: Optional[IAIModelConfigRepository] = None) -> IAIModelConfigRepository:
    """
    获取 AIModelConfigRepository 实例 (依赖注入或默认实例).

    Args:
        repo: 可选的 Repository 实例 (用于依赖注入/测试)

    Returns:
        IAIModelConfigRepository 实例
    """
    if repo:
        return repo

        from infrastructure.repositories import SupabaseConfigRepository

    db_client = await get_async_db_client()
    return SupabaseConfigRepository(db_client)


# ==========================================
# Configuration Management (读操作)
# ==========================================

async def get_model_configs() -> Dict[str, Any]:
    """
    获取所有 AI 模型配置.

    v3.30: DDD Migration
    - 从 model_config_service.py 迁移
    - 改为 async (修复 AIM-CRITICAL-2)
    - 使用 asyncio.gather 并发查询

    Returns:
        Dict with text/image/admin configs
    """
    from shared.ai.model_config import (
        get_text_model_config,
        get_image_model_config,
        get_admin_model_config,
        get_enabled_providers
    )

    try:
        # 并发查询所有配置 (性能优化)
        text, free, starter, pro, admin, providers = await asyncio.gather(
            get_text_model_config(),
            get_image_model_config("t1"),
            get_image_model_config("t2"),
            get_image_model_config("t3"),
            get_admin_model_config(),
            get_enabled_providers(),
        )

        return {
            "text": text,
            "image": {
                "t1": free,
                "t2": starter,
                "t3": pro,
            },
            "admin": admin,
            "enabled_providers": providers,
        }
    except Exception as e:
        logger.error(f"[AI] Failed to get model configs: {e}")
        return {}


# ==========================================
# Configuration Updates (写操作)
# ==========================================

async def update_text_model_config(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    admin_id: Optional[str] = None,
    config_repo: Optional[IAIModelConfigRepository] = None,
) -> Optional[Dict[str, Any]]:
    """
    更新文本模型配置.

    v3.31: Added Repository dependency injection
    v3.30: DDD Migration
    - 从 model_config_service.py 迁移
    - 改为 async (修复 AIM-CRITICAL-2)
    - 实现真实持久化 (修复 AIM-HIGH-1)
    - 添加 Audit Log (修复 AIM-SEC-2)

    Args:
        provider: 提供商名称
        model: 模型名称
        max_tokens: 最大 tokens
        temperature: 温度
        admin_id: 管理员 ID
        config_repo: 可选的 ConfigRepository 实例 (用于依赖注入/测试)

    Returns:
        更新后的配置或 None
    """
    try:
        repo = _get_config_repo(config_repo)

        # 读取当前配置
        current = await repo.get_by_key(CONFIG_KEY_TEXT_MODEL)
        if current:
            import json
            current = json.loads(current)
        else:
            # 默认配置
            current = {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "max_tokens": 4096,
                "temperature": 0.7,
            }

        # 记录旧值 (for audit)
        old_value = current.copy()

        # 更新字段
        if provider:
            current["provider"] = provider
        if model:
            current["model"] = model
        if max_tokens is not None:
            current["max_tokens"] = max_tokens
        if temperature is not None:
            current["temperature"] = temperature

        # 持久化
        import json
        await repo.create(
            key=CONFIG_KEY_TEXT_MODEL,
            value=json.dumps(current),
            group="ai",
            description="User text generation model config",
            value_type="json",
            admin_id=admin_id
        ) if not await repo.get_by_key(CONFIG_KEY_TEXT_MODEL) else await repo.update(
            key=CONFIG_KEY_TEXT_MODEL,
            value=json.dumps(current),
            admin_id=admin_id
        )

        # Audit Log
        await _log_config_change(
            config_key=CONFIG_KEY_TEXT_MODEL,
            action="update",
            old_value=old_value,
            new_value=current,
            admin_id=admin_id
        )

        logger.info(f"[AI] Text model config updated by {admin_id}")
        return current

    except Exception as e:
        logger.error(f"[AI] Failed to update text config: {e}")
        return None


async def update_image_model_config(
    tier: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    admin_id: Optional[str] = None,
    config_repo: Optional[IAIModelConfigRepository] = None,
) -> Optional[Dict[str, Any]]:
    """
    更新图像模型配置.

    v3.31: Added Repository dependency injection
    v3.30: DDD Migration
    - 从 model_config_service.py 迁移
    - 改为 async (修复 AIM-CRITICAL-2)
    - 实现真实持久化 (修复 AIM-HIGH-1)
    - 添加 Audit Log (修复 AIM-SEC-2)

    Args:
        tier: 用户等级 (free/starter/pro/all)
        provider: 提供商名称
        model: 模型名称
        admin_id: 管理员 ID
        config_repo: 可选的 ConfigRepository 实例 (用于依赖注入/测试)

    Returns:
        更新后的配置或 None
    """
    try:
        repo = _get_config_repo(config_repo)

        # 读取当前配置
        current = await repo.get_by_key(CONFIG_KEY_IMAGE_MODEL)
        if current:
            import json
            current = json.loads(current)
        else:
            # 默认配置
            current = {
                "provider": "fal",
                "models": {
                    "t1": "flux-schnell",
                    "t2": "flux-schnell",
                    "t3": "flux-dev"
                }
            }

        # 记录旧值 (for audit)
        old_value = current.copy()

        # 更新字段
        if provider:
            current["provider"] = provider

        if model:
            if "models" not in current:
                current["models"] = {}

            if tier == TIER_ALL:
                # 更新所有等级
                for t in ["t1", "t2", "t3"]:
                    current["models"][t] = model
            else:
                # 更新指定等级
                current["models"][tier] = model

        # 持久化
        import json
        await repo.create(
            key=CONFIG_KEY_IMAGE_MODEL,
            value=json.dumps(current),
            group="ai",
            description="User image generation model config",
            value_type="json",
            admin_id=admin_id
        ) if not await repo.get_by_key(CONFIG_KEY_IMAGE_MODEL) else await repo.update(
            key=CONFIG_KEY_IMAGE_MODEL,
            value=json.dumps(current),
            admin_id=admin_id
        )

        # Audit Log
        await _log_config_change(
            config_key=CONFIG_KEY_IMAGE_MODEL,
            action="update",
            old_value=old_value,
            new_value=current,
            admin_id=admin_id
        )

        logger.info(f"[AI] Image model config updated for tier={tier} by {admin_id}")
        return current

    except Exception as e:
        logger.error(f"[AI] Failed to update image config: {e}")
        return None


async def update_canary_config(
    enabled: bool,
    percentage: int,
    target_model: Optional[str],
    admin_id: Optional[str] = None,
    config_repo: Optional[IAIModelConfigRepository] = None,
) -> Optional[Dict[str, Any]]:
    """
    更新 Canary 灰度配置.

    v3.31: Added Repository dependency injection
    v3.30: DDD Migration
    - 从 api/admin/ai_models.py 迁移 (修复 AIM-CRITICAL-3)
    - 不再直接操作数据库，使用 ConfigRepository
    - 添加 Audit Log (修复 AIM-SEC-2)

    Args:
        enabled: 是否启用
        percentage: 灰度百分比 (0-100)
        target_model: 目标模型
        admin_id: 管理员 ID
        config_repo: 可选的 ConfigRepository 实例 (用于依赖注入/测试)

    Returns:
        更新后的配置或 None
    """
    try:
        repo = _get_config_repo(config_repo)

        # 读取当前配置
        current = await repo.get_by_key(CONFIG_KEY_CANARY)
        if current:
            import json
            old_value = json.loads(current)
        else:
            old_value = None

        # 新配置
        canary_config = {
            "enabled": enabled,
            "percentage": percentage,
            "target_model": target_model
        }

        # 持久化
        import json
        await repo.create(
            key=CONFIG_KEY_CANARY,
            value=json.dumps(canary_config),
            group="ai",
            description="AI Canary rollout configuration",
            value_type="json",
            admin_id=admin_id
        ) if not await repo.get_by_key(CONFIG_KEY_CANARY) else await repo.update(
            key=CONFIG_KEY_CANARY,
            value=json.dumps(canary_config),
            admin_id=admin_id
        )

        # Audit Log
        await _log_config_change(
            config_key=CONFIG_KEY_CANARY,
            action="update",
            old_value=old_value,
            new_value=canary_config,
            admin_id=admin_id
        )

        logger.info(f"[AI] Canary config updated by {admin_id}")
        return canary_config

    except Exception as e:
        logger.error(f"[AI] Failed to update canary config: {e}")
        return None


async def toggle_ai_provider(
    provider: str,
    enabled: bool,
    admin_id: Optional[str] = None,
    config_repo: Optional[IAIModelConfigRepository] = None,
) -> Optional[Dict[str, Any]]:
    """
    切换 AI 提供商状态.

    v3.31: Added Repository dependency injection
    v3.30: DDD Migration
    - 从 model_config_service.py 迁移
    - 改为 async (修复 AIM-CRITICAL-2)
    - 实现真实持久化 (修复 AIM-HIGH-1)
    - 添加 Audit Log (修复 AIM-SEC-2)

    Args:
        provider: 提供商名称
        enabled: 是否启用
        admin_id: 管理员 ID
        config_repo: 可选的 ConfigRepository 实例 (用于依赖注入/测试)

    Returns:
        更新后的状态或 None
    """
    try:
        repo = _get_config_repo(config_repo)

        # 读取当前提供商状态
        current = await repo.get_by_key(CONFIG_KEY_ENABLED_PROVIDERS)
        if current:
            import json
            providers = json.loads(current)
        else:
            # 默认提供商状态
            providers = {
                "openai": True,
                "fal": True,
                "qwen": False,
                "gemini": False,
                "grok": False,
                "jimeng": False,
                "anthropic": False
            }

        # 记录旧值
        old_value = providers.copy()

        # 更新
        providers[provider] = enabled

        # 持久化
        import json
        await repo.create(
            key=CONFIG_KEY_ENABLED_PROVIDERS,
            value=json.dumps(providers),
            group="ai",
            description="Enabled AI providers",
            value_type="json",
            admin_id=admin_id
        ) if not await repo.get_by_key(CONFIG_KEY_ENABLED_PROVIDERS) else await repo.update(
            key=CONFIG_KEY_ENABLED_PROVIDERS,
            value=json.dumps(providers),
            admin_id=admin_id
        )

        # Audit Log
        await _log_config_change(
            config_key=CONFIG_KEY_ENABLED_PROVIDERS,
            action="toggle_provider",
            old_value=old_value,
            new_value=providers,
            admin_id=admin_id
        )

        logger.info(f"[AI] Provider {provider} {'enabled' if enabled else 'disabled'} by {admin_id}")
        return {"provider": provider, "enabled": enabled}

    except Exception as e:
        logger.error(f"[AI] Failed to toggle provider: {e}")
        return None


# ==========================================
# Usage Statistics
# ==========================================

async def get_ai_usage_stats(days: int = 30) -> Dict[str, Any]:
    """
    获取 AI 使用统计.

    v3.30: DDD Migration
    - 从 model_config_service.py 迁移
    - 改为 async (修复 AIM-CRITICAL-2)
    - TODO: 实现真实统计查询 (AIM-HIGH-2)

    Args:
        days: 统计天数

    Returns:
        使用统计数据
    """
    # TODO: 实现真实统计查询
    # 应该查询 ai_usage_logs 表或类似表
    # 统计各提供商使用量、各模型调用次数等

    logger.warning("[AI] Usage stats not implemented, returning mock data")
    return {
        "total_requests": 0,
        "total_tokens": 0,
        "total_images": 0,
        "by_provider": {},
        "by_model": {},
        "period_days": days
    }


# ==========================================
# Cache Management
# ==========================================

async def clear_ai_cache(cache_type: str = "all") -> bool:
    """
    清除 AI 缓存.

    v3.30: DDD Migration
    - 从 model_config_service.py 迁移
    - 改为 async (修复 AIM-CRITICAL-2)
    - 实现 image 分支 (修复 AIM-HIGH-3)

    Args:
        cache_type: 缓存类型 (text/image/all)

    Returns:
        是否成功
    """
    from core.cache import get_cache_provider

    try:
        cache_provider = get_cache_provider()
        redis = getattr(cache_provider, '_client', None) if hasattr(cache_provider, '_client') else None

        if not redis:
            logger.warning("[AI] Redis not available")
            return False

        # 根据类型清除缓存
        if cache_type == "text":
            # 清除文本 AI 缓存
            deleted = 0
            cursor = 0
            while True:
                cursor, keys = redis.scan(cursor, match=CACHE_PREFIX_TEXT + "*", count=100)
                if keys:
                    deleted += redis.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"[AI] Cleared {deleted} text cache keys")

        elif cache_type == "image":
            # 清除图像 AI 缓存 (修复 AIM-HIGH-3)
            deleted = 0
            cursor = 0
            while True:
                cursor, keys = redis.scan(cursor, match=CACHE_PREFIX_IMAGE + "*", count=100)
                if keys:
                    deleted += redis.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"[AI] Cleared {deleted} image cache keys")

        elif cache_type == "all":
            # 清除所有 AI 缓存
            deleted = 0
            cursor = 0
            while True:
                cursor, keys = redis.scan(cursor, match=CACHE_PREFIX_ALL, count=100)
                if keys:
                    deleted += redis.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"[AI] Cleared {deleted} total cache keys")

        return True

    except Exception as e:
        logger.error(f"[AI] Failed to clear cache: {e}")
        return False


# ==========================================
# Helper Functions
# ==========================================

async def _log_config_change(
    config_key: str,
    action: str,
    old_value: Any,
    new_value: Any,
    admin_id: Optional[str]
):
    """
    记录配置变更审计日志.

    v3.30: 新增 (修复 AIM-SEC-2)

    Args:
        config_key: 配置键
        action: 操作类型
        old_value: 旧值
        new_value: 新值
        admin_id: 管理员 ID
    """
    
    if not admin_id:
        return

    try:
        db_client = await get_async_db_client()

        import json
        db_client.table("config_audit_logs").insert({
            "config_key": config_key,
            "action": action,
            "old_value": json.dumps(old_value) if old_value else None,
            "new_value": json.dumps(new_value) if new_value else None,
            "admin_id": admin_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()

        logger.debug(f"[AI] Audit log created for {config_key}")

    except Exception as e:
        logger.warning(f"[AI] Failed to log config change: {e}")
