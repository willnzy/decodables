"""
TierDowngradeService — 降级权限管理

@module domains.subscriptions.tier_downgrade_service
@version 1.0.0

Phase 3 SVC-007 + BR-006: 处理降级时的权限调整与清理.

与 SubscriptionService.downgrade_user_subscription() 配合使用:
- SubscriptionService: 处理 Stripe 订阅变更、退款
- TierDowngradeService: 处理权限收回、积分调整、通知

降级规则 (BR-006):
1. t3→t2: 收回 t3 专属权限, 保留 t2 权限
2. Any→t1: 收回所有付费权限, 清零月度积分
3. 永久积分 (permanent) 不受影响
4. 已上传的内容保留但不可新增超限功能
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TierDowngradeService:
    """降级权限管理服务.

    职责:
    1. 计算降级后失去的功能列表
    2. 调整月度积分配额 (降级到新 Tier 额度)
    3. 记录降级日志
    """

    def __init__(
        self,
        tier_service=None,
        billing_service=None,
    ):
        """初始化.

        Args:
            tier_service: TierService (查询 Tier 配置)
            billing_service: BillingService (积分调整)
        """
        self._tier_service = tier_service
        self._billing_service = billing_service

    async def calculate_feature_changes(
        self,
        from_tier: str,
        to_tier: str,
    ) -> Dict[str, Any]:
        """计算降级后的功能变更.

        Args:
            from_tier: 原 Tier (e.g., "t3")
            to_tier: 目标 Tier (e.g., "t2")

        Returns:
            {
                "lost_features": [...],   # 将失去的功能
                "kept_features": [...],   # 保留的功能
                "changed_features": [...], # 权限变更的功能 (true→trial)
            }
        """
        if not self._tier_service:
            return {"lost_features": [], "kept_features": [], "changed_features": []}

        try:
            from_config = await self._tier_service.get_tier_config(from_tier)
            to_config = await self._tier_service.get_tier_config(to_tier)

            from_features = from_config.get("features", {})
            to_features = to_config.get("features", {})

            lost = []
            kept = []
            changed = []

            for key, from_val in from_features.items():
                to_val = to_features.get(key, False)

                if from_val is True and to_val is False:
                    lost.append(key)
                elif from_val is True and to_val == "trial":
                    changed.append(key)
                elif from_val is True and to_val is True:
                    kept.append(key)
                elif from_val == "trial" and to_val is False:
                    lost.append(key)
                elif from_val == "trial" and to_val == "trial":
                    kept.append(key)

            return {
                "lost_features": lost,
                "kept_features": kept,
                "changed_features": changed,
            }

        except Exception as e:
            logger.warning(
                "TierDowngradeService: calculate_feature_changes failed %s→%s: %s",
                from_tier, to_tier, e,
            )
            return {"lost_features": [], "kept_features": [], "changed_features": []}

    async def calculate_credit_adjustment(
        self,
        from_tier: str,
        to_tier: str,
        current_monthly: int,
    ) -> Dict[str, int]:
        """计算降级后的积分调整.

        Args:
            from_tier: 原 Tier
            to_tier: 目标 Tier
            current_monthly: 当前月度积分余额

        Returns:
            {"new_monthly_quota": int, "excess_to_clear": int}
        """
        if not self._tier_service:
            return {"new_monthly_quota": 0, "excess_to_clear": current_monthly}

        try:
            new_quota = await self._tier_service.get_monthly_credits(to_tier)
            excess = max(0, current_monthly - new_quota)

            return {
                "new_monthly_quota": new_quota,
                "excess_to_clear": excess,
            }

        except Exception as e:
            logger.warning(
                "TierDowngradeService: calculate_credit_adjustment failed: %s", e,
            )
            return {"new_monthly_quota": 0, "excess_to_clear": current_monthly}

    async def get_downgrade_summary(
        self,
        user_id: str,
        from_tier: str,
        to_tier: str,
        current_monthly: int = 0,
    ) -> Dict[str, Any]:
        """生成降级摘要 — 供前端确认界面使用.

        Args:
            user_id: 用户 ID
            from_tier: 原 Tier
            to_tier: 目标 Tier
            current_monthly: 当前月度积分

        Returns:
            完整的降级影响摘要
        """
        feature_changes = await self.calculate_feature_changes(from_tier, to_tier)
        credit_adjustment = await self.calculate_credit_adjustment(
            from_tier, to_tier, current_monthly,
        )

        return {
            "from_tier": from_tier,
            "to_tier": to_tier,
            "feature_changes": feature_changes,
            "credit_adjustment": credit_adjustment,
        }
