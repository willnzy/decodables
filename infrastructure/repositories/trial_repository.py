"""
Trial Repository Implementation — Supabase 实现

@module infrastructure.repositories.trial_repository
@version 1.0.0

Phase 3 REPO-004: 读取 profiles 表中 trial 相关字段.
Trial 配置从 system_configs 表读取 (Admin 驱动, 非硬编码).
"""

import json
import logging
from typing import Any, Dict, Optional

from domains.entitlement.repository import ITrialRepository

logger = logging.getLogger(__name__)


class SupabaseTrialRepository(ITrialRepository):
    """Supabase 实现 — Trial 状态与配置读取."""

    def __init__(self, client):
        """初始化 — 需要 AsyncClient.

        Args:
            client: Supabase AsyncClient
        """
        if client is None:
            raise ValueError("AsyncClient required")
        self.client = client

    async def get_trial_status(
        self, user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取用户试用期状态.

        从 profiles 表读取 trial 相关字段:
        - is_trial_active (BOOLEAN)
        - trial_start_date (TIMESTAMPTZ)
        - trial_end_date (TIMESTAMPTZ)

        Args:
            user_id: 用户 ID (UUID)

        Returns:
            Trial 状态字典, 或 None (用户不存在)
        """
        try:
            result = await (
                self.client.table("profiles")
                .select(
                    "is_trial_active, trial_start_date, trial_end_date, tier",
                )
                .eq("id", user_id)
                .execute()
            )

            if not result.data:
                return None

            row = result.data[0]
            return {
                "is_trial_active": row.get("is_trial_active", False),
                "trial_start_date": row.get("trial_start_date"),
                "trial_end_date": row.get("trial_end_date"),
                "tier": row.get("tier", "t1"),
            }

        except Exception as e:
            logger.warning(
                "[TrialRepo] get_trial_status failed user=%s: %s",
                user_id, e,
            )
            return None

    async def get_trial_config(self) -> Dict[str, Any]:
        """获取 Admin 配置的 trial 参数.

        从 system_configs 表读取:
        - trial.duration_days → 试用期天数 (默认 7)
        - trial.features      → 试用期可用功能列表

        Returns:
            Trial 配置字典, 至少包含 trial_days
        """
        defaults = {
            "trial_days": 7,
            "trial_features": [],
        }

        try:
            # 读取 trial.duration_days
            days_result = await (
                self.client.table("system_configs")
                .select("value")
                .eq("key", "trial.duration_days")
                .eq("is_active", True)
                .execute()
            )

            if days_result.data:
                raw = days_result.data[0].get("value")
                if raw:
                    try:
                        defaults["trial_days"] = int(raw)
                    except (ValueError, TypeError):
                        pass

            # 读取 trial.features (JSON array)
            features_result = await (
                self.client.table("system_configs")
                .select("value")
                .eq("key", "trial.features")
                .eq("is_active", True)
                .execute()
            )

            if features_result.data:
                raw = features_result.data[0].get("value")
                if raw:
                    try:
                        features = json.loads(raw)
                        if isinstance(features, list):
                            defaults["trial_features"] = features
                    except (json.JSONDecodeError, TypeError):
                        pass

            return defaults

        except Exception as e:
            logger.warning(
                "[TrialRepo] get_trial_config failed: %s", e,
            )
            return defaults
