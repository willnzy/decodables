"""
Unified Feature Flag Evaluation Engine

@module core.feature_flag.evaluator
@version 1.0.0

统一评估引擎,处理所有类型的Flag:
- boolean (简单开关)
- multivariate (多变体)
- experiment (A/B实验)

评估流程 (7步):
1. 检查enabled
2. 检查时间窗口
3. 检查环境
4. 检查黑名单
5. 检查白名单 (命中立即返回)
6. 评估定向规则
7. 计算变体分配 (百分比灰度)
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .types import (
    EvaluationContext,
    EvaluationResult,
    EvaluationReason,
    FlagType,
    Variant,
)
from .hasher import get_hash_bucket

logger = logging.getLogger(__name__)


class UnifiedEvaluator:
    """
    统一评估引擎

    处理所有类型的Feature Flag评估
    """

    def evaluate(
        self,
        flag: Dict[str, Any],
        context: EvaluationContext,
    ) -> EvaluationResult:
        """
        评估Flag

        Args:
            flag: Flag配置 (从数据库读取)
            context: 评估上下文 (用户/环境信息)

        Returns:
            EvaluationResult: 评估结果
        """
        flag_key = flag.get("key", "unknown")
        flag_type = FlagType(flag.get("flag_type", "boolean"))

        try:
            # 1. 检查总开关
            if not flag.get("enabled", False):
                return self._result(flag, False, EvaluationReason.DISABLED)

            # 2. 检查时间窗口
            if not self._check_time_window(flag):
                return self._result(flag, False, EvaluationReason.TIME_WINDOW)

            # 3. 检查环境
            if not self._check_environment(flag, context):
                return self._result(flag, False, EvaluationReason.ENVIRONMENT)

            # 4. 检查黑名单
            if self._in_blacklist(flag, context):
                return self._result(flag, False, EvaluationReason.BLACKLIST)

            # 5. 检查白名单 (命中则立即返回treatment)
            if self._in_whitelist(flag, context):
                return self._result(
                    flag, True, EvaluationReason.WHITELIST,
                    variant=self._get_first_treatment_variant(flag)
                )

            # 6. 评估定向规则
            rule_result = self._evaluate_rules(flag, context)
            if rule_result:
                return rule_result

            # 7. 计算变体分配 (百分比灰度)
            return self._assign_variant(flag, context)

        except Exception as e:
            logger.error(f"Flag evaluation error: {flag_key}, {e}", exc_info=True)
            return self._result(flag, False, EvaluationReason.ERROR)

    # ==================== 评估步骤 ====================

    def _check_time_window(self, flag: Dict) -> bool:
        """检查时间窗口"""
        now = datetime.now(timezone.utc)

        start_at = flag.get("start_at")
        if start_at:
            if isinstance(start_at, str):
                start_time = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
            else:
                start_time = start_at
            if now < start_time:
                return False

        end_at = flag.get("end_at")
        if end_at:
            if isinstance(end_at, str):
                end_time = datetime.fromisoformat(end_at.replace("Z", "+00:00"))
            else:
                end_time = end_at
            if now > end_time:
                return False

        return True

    def _check_environment(self, flag: Dict, context: EvaluationContext) -> bool:
        """检查环境"""
        environments = flag.get("environments", [])
        if not environments:
            return True
        return context.environment in environments

    def _in_blacklist(self, flag: Dict, context: EvaluationContext) -> bool:
        """检查黑名单"""
        blacklist = flag.get("blacklist_user_ids", [])
        return context.user_id in blacklist if context.user_id else False

    def _in_whitelist(self, flag: Dict, context: EvaluationContext) -> bool:
        """检查白名单"""
        whitelist = flag.get("whitelist_user_ids", [])
        return context.user_id in whitelist if context.user_id else False

    def _evaluate_rules(
        self,
        flag: Dict,
        context: EvaluationContext
    ) -> Optional[EvaluationResult]:
        """评估定向规则"""
        rules = flag.get("targeting_rules", [])
        if not rules:
            return None

        # 按优先级排序
        sorted_rules = sorted(rules, key=lambda r: r.get("priority", 999))

        for rule in sorted_rules:
            if self._match_rule_conditions(rule, context):
                variant_key = rule.get("variant", "treatment")

                # 规则内也可以有灰度百分比
                rule_percentage = rule.get("rollout_percentage", 100)
                if self._in_rollout(context.identifier, flag["key"], rule_percentage):
                    variant = self._get_variant_by_key(flag, variant_key)
                    return self._result(
                        flag,
                        variant.value if variant else True,
                        EvaluationReason.RULE,
                        variant=variant_key,
                        rule_id=rule.get("id")
                    )

        return None

    def _match_rule_conditions(
        self,
        rule: Dict,
        context: EvaluationContext
    ) -> bool:
        """匹配规则条件 (所有条件必须满足)"""
        conditions = rule.get("conditions", [])

        for condition in conditions:
            if not self._match_condition(condition, context):
                return False

        return True

    def _match_condition(
        self,
        condition: Dict,
        context: EvaluationContext
    ) -> bool:
        """匹配单个条件"""
        attribute = condition.get("attribute")
        operator = condition.get("operator")
        expected = condition.get("value")

        actual = context.get(attribute)

        if actual is None:
            return operator == "not_set"

        # 操作符映射
        operators = {
            "eq": lambda a, e: a == e,
            "neq": lambda a, e: a != e,
            "in": lambda a, e: a in e if isinstance(e, list) else a == e,
            "not_in": lambda a, e: a not in e if isinstance(e, list) else a != e,
            "contains": lambda a, e: e in str(a),
            "not_contains": lambda a, e: e not in str(a),
            "starts_with": lambda a, e: str(a).startswith(e),
            "ends_with": lambda a, e: str(a).endswith(e),
            "gt": lambda a, e: float(a) > float(e),
            "gte": lambda a, e: float(a) >= float(e),
            "lt": lambda a, e: float(a) < float(e),
            "lte": lambda a, e: float(a) <= float(e),
            "regex": lambda a, e: bool(re.match(e, str(a))),
            "not_set": lambda a, e: a is None,
            "is_set": lambda a, e: a is not None,
        }

        try:
            if operator in operators:
                return operators[operator](actual, expected)
            return False
        except Exception:
            return False

    def _assign_variant(
        self,
        flag: Dict,
        context: EvaluationContext
    ) -> EvaluationResult:
        """分配变体 (核心算法)"""
        rollout_percentage = flag.get("rollout_percentage", 0)

        # 检查是否在灰度范围内
        if not self._in_rollout(context.identifier, flag["key"], rollout_percentage):
            return self._result(flag, False, EvaluationReason.PERCENTAGE, variant="control")

        # 按权重分配变体
        variants = flag.get("variants", [])
        if not variants:
            return self._result(flag, True, EvaluationReason.PERCENTAGE, variant="treatment")

        variant = self._select_variant_by_weight(
            context.identifier,
            flag["key"],
            variants
        )

        return self._result(
            flag,
            variant.get("value", True),
            EvaluationReason.PERCENTAGE,
            variant=variant.get("key", "treatment")
        )

    # ==================== 辅助方法 ====================

    def _in_rollout(self, identifier: str, flag_key: str, percentage: int) -> bool:
        """判断是否在灰度范围内"""
        if percentage >= 100:
            return True
        if percentage <= 0:
            return False

        bucket = get_hash_bucket(f"{identifier}:{flag_key}")
        return bucket < percentage

    def _select_variant_by_weight(
        self,
        identifier: str,
        flag_key: str,
        variants: List[Dict]
    ) -> Dict:
        """按权重选择变体"""
        total_weight = sum(v.get("weight", 0) for v in variants)
        if total_weight <= 0:
            return variants[0] if variants else {"key": "control", "value": False}

        bucket = get_hash_bucket(f"{identifier}:{flag_key}:variant")
        variant_bucket = bucket % total_weight

        cumulative = 0
        for variant in variants:
            cumulative += variant.get("weight", 0)
            if variant_bucket < cumulative:
                return variant

        return variants[0]

    def _get_variant_by_key(self, flag: Dict, key: str) -> Optional[Variant]:
        """根据key获取变体"""
        variants = flag.get("variants", [])
        for v in variants:
            if v.get("key") == key:
                return Variant(key=v["key"], value=v.get("value"), weight=v.get("weight", 50))
        return None

    def _get_first_treatment_variant(self, flag: Dict) -> str:
        """获取第一个非control变体"""
        variants = flag.get("variants", [])
        for v in variants:
            if v.get("key") != "control":
                return v.get("key", "treatment")
        return "treatment"

    def _result(
        self,
        flag: Dict,
        enabled: bool,
        reason: EvaluationReason,
        variant: str = None,
        rule_id: str = None,
    ) -> EvaluationResult:
        """构建评估结果"""
        if variant is None:
            variant = "treatment" if enabled else "control"

        # 获取变体值
        value = enabled
        variants = flag.get("variants", [])
        for v in variants:
            if v.get("key") == variant:
                value = v.get("value", enabled)
                break

        return EvaluationResult(
            enabled=enabled,
            variant=variant,
            value=value,
            reason=reason,
            rule_id=rule_id,
            flag_key=flag.get("key"),
            flag_type=FlagType(flag.get("flag_type", "boolean")),
        )
