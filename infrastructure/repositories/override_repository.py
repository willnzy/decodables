"""
Override Repository Implementation — Supabase 实现

@module infrastructure.repositories.override_repository
@version 1.0.0

Phase 3 REPO-003: 实现 3 级权限覆盖查询:
- user_feature_overrides (用户级)
- group_feature_overrides (组级)
- workspace_feature_overrides (Workspace 级)

所有覆盖值存储为 TEXT ('true'/'false'/'trial'), 转换为 Python bool/str.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from domains.entitlement.repository import IOverrideRepository

logger = logging.getLogger(__name__)

# FeatureAccess: True | False | 'trial'
FeatureAccess = Union[bool, str]


def _parse_override_value(raw: str) -> Optional[FeatureAccess]:
    """将 DB 中的 TEXT 值转换为 FeatureAccess.

    Args:
        raw: 'true' | 'false' | 'trial'

    Returns:
        True | False | 'trial' | None (无法解析)
    """
    if raw == "true":
        return True
    elif raw == "false":
        return False
    elif raw == "trial":
        return "trial"
    return None


class SupabaseOverrideRepository(IOverrideRepository):
    """Supabase 实现 — 3 级权限覆盖查询.

    查询时自动过滤已过期的覆盖 (expires_at IS NULL OR expires_at > NOW()).
    """

    def __init__(self, client):
        """初始化 — 需要 AsyncClient.

        Args:
            client: Supabase AsyncClient
        """
        if client is None:
            raise ValueError("AsyncClient required")
        self.client = client

    async def get_user_override(
        self, user_id: str, feature_key: str,
    ) -> Optional[FeatureAccess]:
        """查询用户级权限覆盖."""
        try:
            result = await (
                self.client.table("user_feature_overrides")
                .select("override_value, expires_at")
                .eq("user_id", user_id)
                .eq("feature_key", feature_key)
                .execute()
            )

            if not result.data:
                return None

            row = result.data[0]
            # 检查过期
            if row.get("expires_at") and self._is_expired(row["expires_at"]):
                return None

            return _parse_override_value(row["override_value"])

        except Exception as e:
            logger.warning(
                "[OverrideRepo] get_user_override failed user=%s feature=%s: %s",
                user_id, feature_key, e,
            )
            return None

    async def get_workspace_override(
        self, workspace_id: str, feature_key: str,
    ) -> Optional[FeatureAccess]:
        """查询 Workspace 级权限覆盖."""
        try:
            result = await (
                self.client.table("workspace_feature_overrides")
                .select("override_value, expires_at")
                .eq("workspace_id", workspace_id)
                .eq("feature_key", feature_key)
                .execute()
            )

            if not result.data:
                return None

            row = result.data[0]
            if row.get("expires_at") and self._is_expired(row["expires_at"]):
                return None

            return _parse_override_value(row["override_value"])

        except Exception as e:
            logger.warning(
                "[OverrideRepo] get_workspace_override failed ws=%s feature=%s: %s",
                workspace_id, feature_key, e,
            )
            return None

    async def get_group_override(
        self, group_id: str, feature_key: str,
    ) -> Optional[FeatureAccess]:
        """查询组级权限覆盖."""
        try:
            result = await (
                self.client.table("group_feature_overrides")
                .select("override_value, expires_at")
                .eq("group_id", group_id)
                .eq("feature_key", feature_key)
                .execute()
            )

            if not result.data:
                return None

            row = result.data[0]
            if row.get("expires_at") and self._is_expired(row["expires_at"]):
                return None

            return _parse_override_value(row["override_value"])

        except Exception as e:
            logger.warning(
                "[OverrideRepo] get_group_override failed group=%s feature=%s: %s",
                group_id, feature_key, e,
            )
            return None

    async def get_all_user_overrides(
        self, user_id: str,
    ) -> Dict[str, FeatureAccess]:
        """查询用户所有有效的权限覆盖."""
        try:
            result = await (
                self.client.table("user_feature_overrides")
                .select("feature_key, override_value, expires_at")
                .eq("user_id", user_id)
                .execute()
            )

            if not result.data:
                return {}

            overrides = {}
            for row in result.data:
                if row.get("expires_at") and self._is_expired(row["expires_at"]):
                    continue
                value = _parse_override_value(row["override_value"])
                if value is not None:
                    overrides[row["feature_key"]] = value

            return overrides

        except Exception as e:
            logger.warning(
                "[OverrideRepo] get_all_user_overrides failed user=%s: %s",
                user_id, e,
            )
            return {}

    async def get_user_group_ids(self, user_id: str) -> List[str]:
        """查询用户所属的所有活跃用户组 ID.

        通过 user_group_members 表查询, 关联 user_groups.is_active.
        同时过滤已过期的成员关系.
        """
        try:
            # 查询用户的所有组成员关系
            result = await (
                self.client.table("user_group_members")
                .select("group_id, expires_at")
                .eq("user_id", user_id)
                .execute()
            )

            if not result.data:
                return []

            group_ids = []
            for row in result.data:
                # 过滤已过期成员
                if row.get("expires_at") and self._is_expired(row["expires_at"]):
                    continue
                group_ids.append(str(row["group_id"]))

            return group_ids

        except Exception as e:
            logger.warning(
                "[OverrideRepo] get_user_group_ids failed user=%s: %s",
                user_id, e,
            )
            return []

    @staticmethod
    def _is_expired(expires_at_str: str) -> bool:
        """检查时间戳是否已过期.

        Args:
            expires_at_str: ISO 格式时间戳字符串

        Returns:
            True 如果已过期
        """
        try:
            if isinstance(expires_at_str, str):
                # 处理 Supabase 返回的时间戳格式
                expires_at = datetime.fromisoformat(
                    expires_at_str.replace("Z", "+00:00"),
                )
            else:
                expires_at = expires_at_str

            now = datetime.now(timezone.utc)
            return expires_at <= now
        except (ValueError, TypeError):
            # 解析失败 = 不确定是否过期, 保守地认为未过期
            return False
