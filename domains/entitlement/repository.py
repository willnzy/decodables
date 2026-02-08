"""
Entitlement Repository Interfaces — Phase 3 DDD Port 定义

@module domains.entitlement.repository
@version 1.0.0

Phase 3 REPO-001/003/004: 定义 Override, TierConfig, Trial 数据访问接口.
Infrastructure 层提供 Supabase 具体实现.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

# FeatureAccess: True (有权限), False (无权限), 'trial' (仅试用期)
FeatureAccess = Union[bool, str]


class IOverrideRepository(ABC):
    """Override 数据访问接口 — REPO-003.

    覆盖 3 张表:
    - user_feature_overrides (用户级)
    - group_feature_overrides (组级)
    - workspace_feature_overrides (Workspace 级)
    """

    @abstractmethod
    async def get_user_override(
        self, user_id: str, feature_key: str,
    ) -> Optional[FeatureAccess]:
        """查询用户级权限覆盖.

        Args:
            user_id: 用户 ID (UUID)
            feature_key: 功能 key (e.g., "ai_generate_asset")

        Returns:
            True/False/'trial' or None (无覆盖)
        """
        pass

    @abstractmethod
    async def get_workspace_override(
        self, workspace_id: str, feature_key: str,
    ) -> Optional[FeatureAccess]:
        """查询 Workspace 级权限覆盖.

        Args:
            workspace_id: 工作区 ID (UUID)
            feature_key: 功能 key

        Returns:
            True/False/'trial' or None (无覆盖)
        """
        pass

    @abstractmethod
    async def get_group_override(
        self, group_id: str, feature_key: str,
    ) -> Optional[FeatureAccess]:
        """查询组级权限覆盖.

        Args:
            group_id: 用户组 ID (UUID)
            feature_key: 功能 key

        Returns:
            True/False/'trial' or None (无覆盖)
        """
        pass

    @abstractmethod
    async def get_all_user_overrides(
        self, user_id: str,
    ) -> Dict[str, FeatureAccess]:
        """查询用户所有有效的权限覆盖.

        Args:
            user_id: 用户 ID

        Returns:
            {feature_key: FeatureAccess} 字典
        """
        pass

    @abstractmethod
    async def get_user_group_ids(self, user_id: str) -> List[str]:
        """查询用户所属的所有活跃用户组 ID.

        Args:
            user_id: 用户 ID

        Returns:
            组 ID 列表
        """
        pass


class ITierConfigRepository(ABC):
    """Tier 配置数据访问接口 — REPO-001.

    读取 system_configs 表中 tier.{tier}.features JSON 配置.
    """

    @abstractmethod
    async def get_tier_features(
        self, tier: str,
    ) -> Optional[Dict[str, FeatureAccess]]:
        """获取指定 Tier 的功能权限配置.

        Args:
            tier: Tier 名称 (t1/t2/t3/t4)

        Returns:
            {feature_key: True/False/'trial'} 或 None (未配置)
        """
        pass

    @abstractmethod
    async def get_tier_quotas(
        self, tier: str,
    ) -> Optional[Dict[str, Any]]:
        """获取指定 Tier 的配额配置.

        Args:
            tier: Tier 名称

        Returns:
            配额字典 (e.g., {"maxProjects": 3, "monthlyCredits": 10})
        """
        pass


class ITrialRepository(ABC):
    """Trial 数据访问接口 — REPO-004.

    读取 profiles 表中的 trial 相关字段.
    """

    @abstractmethod
    async def get_trial_status(
        self, user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """获取用户试用期状态.

        Args:
            user_id: 用户 ID

        Returns:
            {"is_trial_active": bool, "trial_start_date": str, "trial_end_date": str}
            或 None (用户不存在)
        """
        pass

    @abstractmethod
    async def get_trial_config(self) -> Dict[str, Any]:
        """获取 Admin 配置的 trial 参数.

        Returns:
            {"trial_days": int, "trial_features": list, ...}
        """
        pass
