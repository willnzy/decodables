"""
Tier Config Repository Implementation — Supabase 实现

@module infrastructure.repositories.tier_config_repository
@version 1.0.0

Phase 3 REPO-001: 读取 system_configs 表中 tier 相关配置.

配置键约定:
- tier.{tier}.features  → JSON, 19 个 FeatureKey 的权限值
- tier.{tier}.quotas    → JSON, 配额 (maxProjects, monthlyCredits 等)

当 DB 不可用时, 上层 TierService 使用 EMERGENCY_TIER_CONFIGS fallback.
本层只负责 DB 读取, 不做 fallback.
"""

import json
import logging
from typing import Any, Dict, Optional, Union

from domains.entitlement.repository import ITierConfigRepository

logger = logging.getLogger(__name__)

FeatureAccess = Union[bool, str]


class SupabaseTierConfigRepository(ITierConfigRepository):
    """Supabase 实现 — Tier 配置读取.

    从 system_configs 表读取 JSON 格式的 tier 配置.
    """

    def __init__(self, client):
        """初始化 — 需要 AsyncClient.

        Args:
            client: Supabase AsyncClient
        """
        if client is None:
            raise ValueError("AsyncClient required")
        self.client = client

    async def get_tier_features(
        self, tier: str,
    ) -> Optional[Dict[str, FeatureAccess]]:
        """获取指定 Tier 的功能权限配置.

        查询 system_configs 表中 key = 'tier.{tier}.features' 的 JSON 值.

        Args:
            tier: Tier 名称 (t1/t2/t3/t4)

        Returns:
            {feature_key: True/False/'trial'} 或 None
        """
        config_key = f"tier.{tier}.features"
        try:
            result = await (
                self.client.table("system_configs")
                .select("value, value_type")
                .eq("key", config_key)
                .eq("is_active", True)
                .execute()
            )

            if not result.data:
                logger.debug(
                    "[TierConfigRepo] No features config for tier=%s", tier,
                )
                return None

            raw_value = result.data[0].get("value")
            if not raw_value:
                return None

            # 解析 JSON
            features = json.loads(raw_value)
            if not isinstance(features, dict):
                logger.warning(
                    "[TierConfigRepo] tier=%s features is not dict: %s",
                    tier, type(features),
                )
                return None

            # 规范化值: "true"→True, "false"→False, "trial"→"trial"
            normalized = {}
            for key, val in features.items():
                if isinstance(val, bool):
                    normalized[key] = val
                elif isinstance(val, str):
                    if val.lower() == "true":
                        normalized[key] = True
                    elif val.lower() == "false":
                        normalized[key] = False
                    elif val.lower() == "trial":
                        normalized[key] = "trial"
                    else:
                        normalized[key] = val
                else:
                    normalized[key] = bool(val)

            return normalized

        except json.JSONDecodeError as e:
            logger.warning(
                "[TierConfigRepo] JSON parse error for tier=%s: %s", tier, e,
            )
            return None
        except Exception as e:
            logger.warning(
                "[TierConfigRepo] get_tier_features failed tier=%s: %s", tier, e,
            )
            return None

    async def get_tier_quotas(
        self, tier: str,
    ) -> Optional[Dict[str, Any]]:
        """获取指定 Tier 的配额配置.

        查询 system_configs 表中 key = 'tier.{tier}.quotas' 的 JSON 值.

        Args:
            tier: Tier 名称

        Returns:
            配额字典 或 None
        """
        config_key = f"tier.{tier}.quotas"
        try:
            result = await (
                self.client.table("system_configs")
                .select("value, value_type")
                .eq("key", config_key)
                .eq("is_active", True)
                .execute()
            )

            if not result.data:
                logger.debug(
                    "[TierConfigRepo] No quotas config for tier=%s", tier,
                )
                return None

            raw_value = result.data[0].get("value")
            if not raw_value:
                return None

            quotas = json.loads(raw_value)
            if not isinstance(quotas, dict):
                logger.warning(
                    "[TierConfigRepo] tier=%s quotas is not dict", tier,
                )
                return None

            return quotas

        except json.JSONDecodeError as e:
            logger.warning(
                "[TierConfigRepo] JSON parse error for tier=%s quotas: %s",
                tier, e,
            )
            return None
        except Exception as e:
            logger.warning(
                "[TierConfigRepo] get_tier_quotas failed tier=%s: %s", tier, e,
            )
            return None
