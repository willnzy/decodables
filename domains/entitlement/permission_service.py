"""
PermissionService — 统一权限入口

@module domains.entitlement.permission_service
@version 1.0.0

Phase 3 SVC-001: 提供单一入口 check_access(), 内部委托 PriorityEvaluator.

用法:
    service = PermissionService(
        priority_evaluator=evaluator,
        user_repo=user_repo,
    )
    access = await service.check_access(user_id, "ai_generate_asset")
    # True | False | 'trial'
"""

import logging
from typing import Any, Dict, List, Optional, Union

from .priority_evaluator import EvaluationContext, FeatureAccess, PriorityEvaluator

logger = logging.getLogger(__name__)


class PermissionService:
    """统一权限服务 — 所有功能权限检查的唯一入口.

    职责:
    1. 构建 EvaluationContext (从 user_id 查询 tier, trial 状态等)
    2. 委托 PriorityEvaluator 进行 7 层评估
    3. 提供批量检查、缓存等便捷方法

    调用方 (API / Service 层) 只需调用:
        await permission_service.check_access(user_id, feature_key)
    无需关心内部评估逻辑。
    """

    def __init__(
        self,
        priority_evaluator: PriorityEvaluator,
        user_repo=None,
        trial_helper=None,
    ):
        self._evaluator = priority_evaluator
        self._user_repo = user_repo
        self._trial_helper = trial_helper

    async def check_access(
        self,
        user_id: str,
        feature_key: str,
        tier: Optional[str] = None,
        is_trial_active: Optional[bool] = None,
        workspace_id: Optional[str] = None,
    ) -> FeatureAccess:
        """检查用户对某功能的访问权限.

        Args:
            user_id: 用户 ID
            feature_key: 功能 key (e.g., "ai_generate_asset")
            tier: 用户当前 tier (如果已知, 避免重复查询)
            is_trial_active: 是否在试用期 (如果已知)
            workspace_id: 工作区 ID (可选, 用于工作区级覆盖)

        Returns:
            True (有权限), False (无权限), 'trial' (仅试用期)
        """
        # 构建评估上下文
        context = await self._build_context(
            user_id, tier, is_trial_active, workspace_id,
        )

        # 委托 PriorityEvaluator
        return await self._evaluator.evaluate(feature_key, context)

    async def check_access_batch(
        self,
        user_id: str,
        feature_keys: List[str],
        tier: Optional[str] = None,
        is_trial_active: Optional[bool] = None,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, FeatureAccess]:
        """批量检查多个功能权限 — 共享同一个 context 避免重复查询.

        Returns:
            {feature_key: FeatureAccess} 字典
        """
        context = await self._build_context(
            user_id, tier, is_trial_active, workspace_id,
        )

        results = {}
        for key in feature_keys:
            results[key] = await self._evaluator.evaluate(key, context)
        return results

    async def get_all_permissions(
        self,
        user_id: str,
        tier: Optional[str] = None,
        is_trial_active: Optional[bool] = None,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, FeatureAccess]:
        """获取用户所有 19 个 FeatureKey 的权限状态.

        Returns:
            {feature_key: FeatureAccess} 完整权限映射
        """
        from domains.identity.tier_service import FeatureKey

        all_keys = [fk.value for fk in FeatureKey]
        return await self.check_access_batch(
            user_id, all_keys, tier, is_trial_active, workspace_id,
        )

    async def _build_context(
        self,
        user_id: str,
        tier: Optional[str] = None,
        is_trial_active: Optional[bool] = None,
        workspace_id: Optional[str] = None,
    ) -> EvaluationContext:
        """构建评估上下文 — 如果 tier/trial 未提供则从 repo 查询."""
        resolved_tier = tier or "t1"
        resolved_trial = is_trial_active if is_trial_active is not None else False

        # 如果调用方没有提供 tier/trial, 尝试从 user_repo 查询
        if (tier is None or is_trial_active is None) and self._user_repo:
            try:
                user_data = await self._user_repo.get_by_id(user_id)
                if user_data:
                    if tier is None:
                        resolved_tier = user_data.get("tier", "t1")
                    if is_trial_active is None and self._trial_helper:
                        resolved_trial = self._trial_helper(user_data)
            except Exception as e:
                logger.warning(
                    "PermissionService: failed to fetch user data for %s: %s",
                    user_id, e,
                )

        return EvaluationContext(
            user_id=user_id,
            tier=resolved_tier,
            is_trial_active=resolved_trial,
            workspace_id=workspace_id,
        )
