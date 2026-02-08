"""
TrialService — 试用期生命周期管理

@module domains.entitlement.trial_service
@version 1.0.0

Phase 3 SVC-005: 封装试用期逻辑, 提供统一的试用期管理接口.

底层委托 trial_helper.py (已有) + TrialRepository (Phase 3 新增).
trial_days 从 Admin 配置读取 (system_configs.trial.duration_days), 非硬编码.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from domains.identity.trial_helper import is_user_in_trial

logger = logging.getLogger(__name__)


class TrialService:
    """试用期生命周期管理服务.

    职责:
    1. 判断用户是否在试用期 (is_in_trial)
    2. 获取剩余试用天数 (get_remaining_days)
    3. 读取 Admin 配置的试用期参数 (get_trial_config)
    4. 作为 PermissionService 的 trial_helper 回调使用

    设计原则:
    - trial_days 从 DB system_configs 读取 (Admin 驱动)
    - 仅 t1 用户有试用期概念
    - 试用期基于 created_at 计算 (per-user, 非 per-feature)
    """

    def __init__(
        self,
        trial_repo=None,
        tier_service=None,
    ):
        """初始化.

        Args:
            trial_repo: TrialRepository (可选, 用于读取 DB 配置)
            tier_service: TierService (可选, 用于读取 trial.duration_days)
        """
        self._trial_repo = trial_repo
        self._tier_service = tier_service

    async def is_in_trial(self, user_data: Dict[str, Any]) -> bool:
        """判断用户是否在试用期内.

        Args:
            user_data: 用户字典, 至少包含 'tier' 和 'created_at'

        Returns:
            True 如果 t1 用户在试用期内
        """
        trial_days = await self._get_trial_days()
        return is_user_in_trial(user_data, trial_days=trial_days)

    def is_in_trial_sync(self, user_data: Dict[str, Any]) -> bool:
        """同步版本 — 使用默认 trial_days (30天).

        供 PermissionService._build_context 的 trial_helper 回调使用.

        Args:
            user_data: 用户字典

        Returns:
            True 如果 t1 用户在试用期内
        """
        return is_user_in_trial(user_data)

    async def get_remaining_days(self, user_data: Dict[str, Any]) -> int:
        """获取剩余试用天数.

        Args:
            user_data: 用户字典, 至少包含 'tier' 和 'created_at'

        Returns:
            剩余天数 (0 表示试用期已过或不在试用期)
        """
        # 仅 t1 用户
        if user_data.get("tier", "t1") != "t1":
            return 0

        created_at = user_data.get("created_at")
        if not created_at:
            return 0

        try:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00"),
                )

            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            trial_days = await self._get_trial_days()
            trial_end = created_at + timedelta(days=trial_days)
            now = datetime.now(timezone.utc)

            remaining = (trial_end - now).total_seconds() / (24 * 3600)
            return max(0, int(remaining))

        except (ValueError, TypeError) as e:
            logger.warning("TrialService: failed to compute remaining days: %s", e)
            return 0

    async def get_trial_config(self) -> Dict[str, Any]:
        """获取 Admin 配置的试用期参数.

        Returns:
            {"trial_days": int, "trial_features": list}
        """
        if self._trial_repo:
            try:
                return await self._trial_repo.get_trial_config()
            except Exception as e:
                logger.warning("TrialService: get_trial_config failed: %s", e)

        # Fallback
        return {
            "trial_days": await self._get_trial_days(),
            "trial_features": [],
        }

    async def _get_trial_days(self) -> int:
        """读取 Admin 配置的试用天数.

        优先级: tier_service > trial_repo > 默认 30 天
        """
        # 优先从 TierService 读取 (已有缓存)
        if self._tier_service:
            try:
                return await self._tier_service.get_trial_duration_days()
            except Exception:
                pass

        # 从 TrialRepository 读取
        if self._trial_repo:
            try:
                config = await self._trial_repo.get_trial_config()
                return config.get("trial_days", 30)
            except Exception:
                pass

        # 默认值 (与 constants.py DEFAULT_TRIAL_DURATION_DAYS 一致)
        return 30
