"""
Canary Release Logic for AI Models
AI 模型灰度发布逻辑

Provides:
- Deterministic traffic splitting based on user ID
- Support for targeting specific user tiers
- Configuration-driven canary settings

⚠️ v2.0: All functions are now async using ConfigService
"""

import hashlib
import logging
from typing import Tuple, Optional, Dict, Any

from domains.platform.config_service import ConfigService
from infrastructure.repositories.config_repository import SupabaseConfigRepository
from core.database import get_async_db_client

logger = logging.getLogger(__name__)


# Global ConfigService instance (lazy initialized)
_config_service: Optional[ConfigService] = None


async def _get_config_service() -> ConfigService:
    """Get or create global ConfigService instance (async)."""
    global _config_service
    if _config_service is None:
        db_client = await get_async_db_client()
        config_repo = SupabaseConfigRepository(db_client)
        _config_service = ConfigService(config_repo)
    return _config_service


# ==========================================
# Canary Release Functions (Async)
# ==========================================

async def get_canary_config() -> Dict[str, Any]:
    """
    获取灰度发布配置

    Returns:
        {
            "enabled": False,
            "text_reasoning": {
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 10,
                "target_tiers": ["t3"]
            },
            "image_generation": {
                "canary_provider": "jimeng",
                "canary_model": "jimeng-2.1",
                "traffic_percent": 5,
                "target_tiers": ["t3"]
            }
        }
    """
    config_service = await _get_config_service()
    return await config_service.get_config("ai_model.canary") or {"enabled": False}


async def should_use_canary(
    user_id: str,
    model_type: str,
    tier: str = "t1"
) -> Tuple[bool, Optional[Dict[str, str]]]:
    """
    判断是否应该使用灰度模型

    基于用户 ID 的确定性哈希分流,确保同一用户始终获得相同的分配结果。

    Args:
        user_id: 用户 ID (或 visitor_xxx)
        model_type: 模型类型 ('text_reasoning' | 'image_generation')
        tier: 用户等级 ('t1', 't2', 't3')

    Returns:
        (should_use_canary, canary_config)
        - should_use_canary: 是否使用灰度模型
        - canary_config: {"provider": "qwen", "model": "qwen-plus"} 或 None
    """
    # 获取灰度配置
    canary_config = await get_canary_config()

    # 检查是否启用
    if not canary_config.get("enabled", False):
        return False, None

    # 获取对应模型类型的灰度配置
    model_canary = canary_config.get(model_type)
    if not model_canary:
        logger.debug(f"[Canary] No canary config for model_type: {model_type}")
        return False, None

    # 检查目标 tier
    target_tiers = model_canary.get("target_tiers", [])
    if target_tiers and tier not in target_tiers:
        logger.debug(f"[Canary] User tier '{tier}' not in target_tiers: {target_tiers}")
        return False, None

    # 获取流量百分比
    traffic_percent = model_canary.get("traffic_percent", 0)
    if traffic_percent <= 0:
        return False, None

    # 基于用户 ID 的确定性分流
    user_bucket = _get_user_bucket(user_id, model_type)

    if user_bucket < traffic_percent:
        logger.info(f"[Canary] User {user_id[:8]}... assigned to canary (bucket={user_bucket}, threshold={traffic_percent})")
        return True, {
            "provider": model_canary["canary_provider"],
            "model": model_canary["canary_model"]
        }

    logger.debug(f"[Canary] User {user_id[:8]}... assigned to control (bucket={user_bucket}, threshold={traffic_percent})")
    return False, None


def _get_user_bucket(user_id: str, model_type: str) -> int:
    """
    计算用户的分流桶 (0-99)

    使用 MD5 哈希确保:
    1. 同一用户在同一模型类型下始终获得相同的桶
    2. 分布均匀
    3. 不同模型类型的分配相互独立

    Args:
        user_id: 用户 ID
        model_type: 模型类型

    Returns:
        0-99 的整数
    """
    # 组合用户 ID 和模型类型
    hash_input = f"{user_id}:{model_type}:canary"

    # MD5 哈希
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()

    # 取前 8 位转换为整数,然后取模 100
    bucket = int(hash_value[:8], 16) % 100

    return bucket


async def get_effective_model_config(
    user_id: str,
    model_type: str,
    tier: str,
    base_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    获取考虑灰度后的有效模型配置

    这是一个便捷函数,自动处理灰度判断和配置合并。

    Args:
        user_id: 用户 ID
        model_type: 模型类型 ('text_reasoning' | 'image_generation')
        tier: 用户等级
        base_config: 基础配置 (从 model_config.py 获取)

    Returns:
        有效的模型配置,可能是基础配置或灰度配置
    """
    use_canary, canary_config = await should_use_canary(user_id, model_type, tier)

    if use_canary and canary_config:
        # 返回灰度配置
        return {
            **base_config,
            "provider": canary_config["provider"],
            "model": canary_config["model"],
            "is_canary": True
        }

    # 返回基础配置
    return {
        **base_config,
        "is_canary": False
    }


# ==========================================
# Admin Functions (Async)
# ==========================================

async def get_canary_status() -> Dict[str, Any]:
    """
    获取灰度发布状态 (用于 Admin 面板)

    Returns:
        {
            "enabled": True/False,
            "text_reasoning": {
                "enabled": True,
                "canary_provider": "qwen",
                "canary_model": "qwen-plus",
                "traffic_percent": 10,
                "target_tiers": ["t3"]
            },
            "image_generation": {...}
        }
    """
    config = await get_canary_config()

    status = {
        "enabled": config.get("enabled", False)
    }

    for model_type in ["text_reasoning", "image_generation"]:
        model_canary = config.get(model_type, {})
        status[model_type] = {
            "enabled": bool(model_canary.get("canary_provider")),
            "canary_provider": model_canary.get("canary_provider", ""),
            "canary_model": model_canary.get("canary_model", ""),
            "traffic_percent": model_canary.get("traffic_percent", 0),
            "target_tiers": model_canary.get("target_tiers", [])
        }

    return status
