"""
PriorityEvaluator — 7 层优先级权限评估引擎

@module domains.entitlement.priority_evaluator
@version 1.0.0

Phase 3 SVC-004 + BR-002: 实现 ground-truth.json 定义的 7 层优先级:
  L1 user_override > L2 feature_flag > L3 tier_config > L4 feature_gate
  > L5 trial_status > L6 promotion > L7 default(false)

每层返回 FeatureAccess (True | False | 'trial' | None):
- None = 该层无意见, 继续下一层
- 非 None = 立即返回, 不再评估后续层

用法:
    evaluator = PriorityEvaluator(
        override_repo=override_repo,
        flag_service=flag_service,
        tier_service=tier_service,
    )
    access = await evaluator.evaluate(user_id, feature_key, context)
"""

import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

# FeatureAccess: True (有权限), False (无权限), 'trial' (仅试用期)
FeatureAccess = Union[bool, str]


class EvaluationContext:
    """评估上下文 — 携带用户相关信息, 避免每层重复查询."""

    def __init__(
        self,
        user_id: str,
        tier: str = "t1",
        is_trial_active: bool = False,
        workspace_id: Optional[str] = None,
        group_ids: Optional[list] = None,
    ):
        self.user_id = user_id
        self.tier = tier
        self.is_trial_active = is_trial_active
        self.workspace_id = workspace_id
        self.group_ids = group_ids or []


class PriorityEvaluator:
    """7 层优先级权限评估引擎.

    优先级顺序 (高→低):
    L1. user_override    — Admin 为特定用户设置的覆盖 (user_feature_overrides)
    L2. feature_flag     — Kill Switch / 功能开关 (feature_flags 表)
    L3. tier_config      — 当前 Tier 的功能配置 (system_configs / EMERGENCY fallback)
    L4. feature_gate     — 灰度发布 / 百分比放量 (feature_flags.rollout_percentage)
    L5. trial_status     — 试用期特殊权限 (仅 t1, 试用期内返回 'trial')
    L6. promotion        — 促销活动临时权限 (campaigns 表, 有效期内)
    L7. default           — 默认值 False

    设计原则:
    - 每层评估独立, 返回 None 表示 "该层无意见, 交给下一层"
    - 第一个返回非 None 的层级决定最终结果
    - Graceful Degradation: 任何层查询失败 = 返回 None, 继续下一层
    """

    def __init__(
        self,
        override_repo=None,
        flag_service=None,
        tier_service=None,
    ):
        self._override_repo = override_repo
        self._flag_service = flag_service
        self._tier_service = tier_service

    async def evaluate(
        self,
        feature_key: str,
        context: EvaluationContext,
    ) -> FeatureAccess:
        """评估用户对某功能的访问权限.

        Args:
            feature_key: 功能 key (e.g., "ai_generate_asset")
            context: 评估上下文 (包含 user_id, tier, is_trial_active 等)

        Returns:
            True (有权限), False (无权限), 'trial' (仅试用期)
        """
        # 按优先级依次评估 7 层
        layers = [
            ("L1_override", self._eval_override),
            ("L2_flag", self._eval_flag),
            ("L3_tier", self._eval_tier),
            ("L4_gate", self._eval_gate),
            ("L5_trial", self._eval_trial),
            ("L6_promotion", self._eval_promotion),
            ("L7_default", self._eval_default),
        ]

        for layer_name, evaluator in layers:
            try:
                result = await evaluator(feature_key, context)
                if result is not None:
                    logger.debug(
                        "PriorityEvaluator: %s → %s for user=%s feature=%s",
                        layer_name, result, context.user_id, feature_key,
                    )
                    return result
            except Exception as e:
                # Graceful degradation: 该层失败 = 跳过, 继续下一层
                logger.warning(
                    "PriorityEvaluator: %s failed for user=%s feature=%s: %s",
                    layer_name, context.user_id, feature_key, e,
                )
                continue

        # 不应到达这里 (L7_default 总是返回 False), 但作为安全兜底
        return False

    # ────────────────────────────────────────────────
    # L1: User Override (user_feature_overrides 表)
    # ────────────────────────────────────────────────
    async def _eval_override(
        self, feature_key: str, ctx: EvaluationContext,
    ) -> Optional[FeatureAccess]:
        """查询 user/group/workspace 级别的覆盖设置."""
        if not self._override_repo:
            return None

        # 1) 用户级覆盖 (最高优先级)
        user_override = await self._override_repo.get_user_override(
            ctx.user_id, feature_key,
        )
        if user_override is not None:
            return user_override

        # 2) 工作区级覆盖
        if ctx.workspace_id:
            ws_override = await self._override_repo.get_workspace_override(
                ctx.workspace_id, feature_key,
            )
            if ws_override is not None:
                return ws_override

        # 3) 组级覆盖
        for group_id in ctx.group_ids:
            group_override = await self._override_repo.get_group_override(
                group_id, feature_key,
            )
            if group_override is not None:
                return group_override

        return None

    # ────────────────────────────────────────────────
    # L2: Feature Flag (Kill Switch)
    # ────────────────────────────────────────────────
    async def _eval_flag(
        self, feature_key: str, ctx: EvaluationContext,
    ) -> Optional[FeatureAccess]:
        """检查功能开关 — 如果开关关闭则强制禁用 (Kill Switch)."""
        if not self._flag_service:
            return None

        flag = await self._flag_service.get_flag_by_key(feature_key)
        if flag is None:
            return None  # 没有对应 flag, 不影响

        if not flag.enabled:
            # Kill Switch 触发: 功能被全局禁用
            return False

        return None  # Flag 开启但不决定权限, 交给下一层

    # ────────────────────────────────────────────────
    # L3: Tier Config (当前 Tier 的功能权限)
    # ────────────────────────────────────────────────
    async def _eval_tier(
        self, feature_key: str, ctx: EvaluationContext,
    ) -> Optional[FeatureAccess]:
        """查询当前 Tier 的功能配置.

        使用 get_feature_access() (SVC-002) 保留 'trial' 标记,
        而非 can_use_feature() 的 bool 解析结果.
        """
        if not self._tier_service:
            return None

        # 优先使用 get_feature_access (返回 True/False/'trial'/None)
        if hasattr(self._tier_service, "get_feature_access"):
            access = await self._tier_service.get_feature_access(
                ctx.tier, feature_key, ctx.is_trial_active,
            )
        else:
            # Fallback: can_use_feature 返回 True/False
            access = await self._tier_service.can_use_feature(
                ctx.tier, feature_key, ctx.is_trial_active,
            )

        if access is not None:
            return access

        return None

    # ────────────────────────────────────────────────
    # L4: Feature Gate (灰度发布 / 百分比放量)
    # ────────────────────────────────────────────────
    async def _eval_gate(
        self, feature_key: str, ctx: EvaluationContext,
    ) -> Optional[FeatureAccess]:
        """百分比放量评估 — 基于 user_id hash 的桶分配."""
        if not self._flag_service:
            return None

        flag = await self._flag_service.get_flag_by_key(feature_key)
        if flag is None or not flag.enabled:
            return None

        # 检查 rollout_percentage
        rollout = getattr(flag, "rollout_percentage", None)
        if rollout is None or rollout >= 100:
            return None  # 全量或无百分比设置, 不影响

        # 基于 user_id hash 的确定性桶分配
        bucket = hash(f"{ctx.user_id}:{feature_key}") % 100
        if bucket < rollout:
            return True  # 在放量范围内
        else:
            return False  # 不在放量范围内

        return None

    # ────────────────────────────────────────────────
    # L5: Trial Status (试用期特殊权限)
    # ────────────────────────────────────────────────
    async def _eval_trial(
        self, feature_key: str, ctx: EvaluationContext,
    ) -> Optional[FeatureAccess]:
        """试用期评估 — 仅 t1 用户在试用期内享有 'trial' 权限."""
        # 仅 t1 用户有试用期概念
        if ctx.tier != "t1":
            return None

        if ctx.is_trial_active:
            # 试用期内: 返回 'trial' (前端可据此显示试用标记)
            return "trial"

        # 试用期已过: 不影响, 交给下一层
        return None

    # ────────────────────────────────────────────────
    # L6: Promotion (促销活动临时权限)
    # ────────────────────────────────────────────────
    async def _eval_promotion(
        self, feature_key: str, ctx: EvaluationContext,
    ) -> Optional[FeatureAccess]:
        """促销活动评估 — Phase 3 预留接口, 暂返回 None."""
        # TODO: Phase 后续实现 — 查询 campaigns 表中的活动权限
        return None

    # ────────────────────────────────────────────────
    # L7: Default (兜底默认值)
    # ────────────────────────────────────────────────
    async def _eval_default(
        self, feature_key: str, ctx: EvaluationContext,
    ) -> Optional[FeatureAccess]:
        """默认值 — 始终返回 False (无权限)."""
        return False
