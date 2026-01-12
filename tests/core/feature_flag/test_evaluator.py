"""
Feature Flag Evaluator Tests - Tier Filtering

@module tests.core.feature_flag.test_evaluator
@version 1.2.0

测试 UnifiedEvaluator 的 Tier 分层筛选功能
"""

import pytest
from core.feature_flag.evaluator import UnifiedEvaluator
from core.feature_flag.types import EvaluationContext, EvaluationReason


class TestTierFiltering:
    """Tier 分层筛选测试"""

    @pytest.fixture
    def evaluator(self):
        return UnifiedEvaluator()

    @pytest.fixture
    def base_flag(self):
        """基础 Flag 配置"""
        return {
            "key": "test_flag",
            "name": "Test Flag",
            "flag_type": "boolean",
            "enabled": True,
            "archived": False,
            "environments": ["production"],
            "rollout_percentage": 100,
            "whitelist_user_ids": [],
            "blacklist_user_ids": [],
            "allowed_tiers": [],
            "targeting_rules": [],
            "variants": [
                {"key": "control", "value": False, "weight": 50},
                {"key": "treatment", "value": True, "weight": 50}
            ]
        }

    # ==================== 顶层 allowed_tiers 测试 ====================

    def test_allowed_tiers_empty_allows_all(self, evaluator, base_flag):
        """空 allowed_tiers 允许所有用户"""
        base_flag["allowed_tiers"] = []

        # t1 用户
        context = EvaluationContext(user_id="u1", tier="t1", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason != EvaluationReason.TIER_MISMATCH

        # t3 用户
        context = EvaluationContext(user_id="u2", tier="t3", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason != EvaluationReason.TIER_MISMATCH

    def test_allowed_tiers_filters_non_matching(self, evaluator, base_flag):
        """allowed_tiers 过滤不匹配的 Tier"""
        base_flag["allowed_tiers"] = ["t3"]

        # t1 用户应该被过滤
        context = EvaluationContext(user_id="u1", tier="t1", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.TIER_MISMATCH
        assert result.enabled is False

        # t2 用户应该被过滤
        context = EvaluationContext(user_id="u2", tier="t2", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.TIER_MISMATCH
        assert result.enabled is False

    def test_allowed_tiers_allows_matching(self, evaluator, base_flag):
        """allowed_tiers 允许匹配的 Tier"""
        base_flag["allowed_tiers"] = ["t2", "t3"]

        # t2 用户允许
        context = EvaluationContext(user_id="u1", tier="t2", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason != EvaluationReason.TIER_MISMATCH

        # t3 用户允许
        context = EvaluationContext(user_id="u2", tier="t3", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason != EvaluationReason.TIER_MISMATCH

    def test_allowed_tiers_case_insensitive(self, evaluator, base_flag):
        """Tier 比较忽略大小写"""
        base_flag["allowed_tiers"] = ["T3"]

        context = EvaluationContext(user_id="u1", tier="t3", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason != EvaluationReason.TIER_MISMATCH

    def test_allowed_tiers_no_tier_in_context(self, evaluator, base_flag):
        """用户上下文无 Tier 信息时，有限制则拒绝"""
        base_flag["allowed_tiers"] = ["t3"]

        # 无 tier 信息
        context = EvaluationContext(user_id="u1", tier=None, environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.TIER_MISMATCH
        assert result.enabled is False

    def test_allowed_tiers_no_tier_but_no_restriction(self, evaluator, base_flag):
        """无 Tier 信息但无限制时允许"""
        base_flag["allowed_tiers"] = []

        context = EvaluationContext(user_id="u1", tier=None, environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason != EvaluationReason.TIER_MISMATCH

    # ==================== 规则级 tiers 测试 ====================

    def test_rule_level_tiers_matches(self, evaluator, base_flag):
        """规则级 tiers 匹配时命中规则"""
        base_flag["allowed_tiers"] = []  # 顶层不限制
        base_flag["rollout_percentage"] = 0  # 默认关闭
        base_flag["targeting_rules"] = [
            {
                "id": "rule_pro",
                "priority": 1,
                "tiers": ["t3"],  # 规则级限制
                "conditions": [],
                "rollout_percentage": 100,
                "variant": "treatment"
            }
        ]

        # t3 用户命中规则
        context = EvaluationContext(user_id="u1", tier="t3", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.RULE
        assert result.enabled is True
        assert result.rule_id == "rule_pro"

    def test_rule_level_tiers_not_matches(self, evaluator, base_flag):
        """规则级 tiers 不匹配时跳过规则"""
        base_flag["allowed_tiers"] = []
        base_flag["rollout_percentage"] = 0
        base_flag["targeting_rules"] = [
            {
                "id": "rule_pro",
                "priority": 1,
                "tiers": ["t3"],
                "conditions": [],
                "rollout_percentage": 100,
                "variant": "treatment"
            }
        ]

        # t1 用户不命中规则，进入默认百分比分配
        context = EvaluationContext(user_id="u1", tier="t1", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.PERCENTAGE
        assert result.enabled is False  # rollout_percentage=0

    def test_rule_level_tiers_with_conditions(self, evaluator, base_flag):
        """规则级 tiers 与 conditions 结合"""
        base_flag["allowed_tiers"] = []
        base_flag["rollout_percentage"] = 0
        base_flag["targeting_rules"] = [
            {
                "id": "rule_pro_us",
                "priority": 1,
                "tiers": ["t3"],
                "conditions": [
                    {"attribute": "country", "operator": "eq", "value": "US"}
                ],
                "rollout_percentage": 100,
                "variant": "treatment"
            }
        ]

        # t3 + US 用户命中
        context = EvaluationContext(
            user_id="u1", tier="t3", country="US", environment="production"
        )
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.RULE

        # t3 + CN 用户不命中 (country 不匹配)
        context = EvaluationContext(
            user_id="u2", tier="t3", country="CN", environment="production"
        )
        result = evaluator.evaluate(base_flag, context)
        assert result.reason != EvaluationReason.RULE

        # t1 + US 用户不命中 (tier 不匹配)
        context = EvaluationContext(
            user_id="u3", tier="t1", country="US", environment="production"
        )
        result = evaluator.evaluate(base_flag, context)
        assert result.reason != EvaluationReason.RULE

    def test_rule_level_multiple_tiers(self, evaluator, base_flag):
        """规则级 tiers 支持多选"""
        base_flag["allowed_tiers"] = []
        base_flag["rollout_percentage"] = 0
        base_flag["targeting_rules"] = [
            {
                "id": "rule_paid",
                "priority": 1,
                "tiers": ["t2", "t3", "t4"],  # 所有付费用户
                "conditions": [],
                "rollout_percentage": 100,
                "variant": "treatment"
            }
        ]

        # t2 用户命中
        context = EvaluationContext(user_id="u1", tier="t2", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.RULE

        # t3 用户命中
        context = EvaluationContext(user_id="u2", tier="t3", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.RULE

        # t1 用户不命中
        context = EvaluationContext(user_id="u3", tier="t1", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason != EvaluationReason.RULE

    # ==================== 顶层 + 规则级组合测试 ====================

    def test_top_level_tier_blocks_before_rules(self, evaluator, base_flag):
        """顶层 Tier 限制在规则评估之前"""
        base_flag["allowed_tiers"] = ["t3"]  # 顶层只允许 t3
        base_flag["targeting_rules"] = [
            {
                "id": "rule_all",
                "priority": 1,
                "tiers": [],  # 规则级不限制
                "conditions": [],
                "rollout_percentage": 100,
                "variant": "treatment"
            }
        ]

        # t1 用户被顶层限制拦截，不会进入规则评估
        context = EvaluationContext(user_id="u1", tier="t1", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.TIER_MISMATCH
        assert result.enabled is False

    def test_whitelist_bypasses_tier_check(self, evaluator, base_flag):
        """白名单绕过 Tier 检查 (白名单在 Tier 检查之后)"""
        base_flag["allowed_tiers"] = ["t3"]
        base_flag["whitelist_user_ids"] = ["u1"]

        # 注意：按当前评估顺序，Tier 检查在白名单之前
        # 所以 t1 用户即使在白名单中，也会被 Tier 限制拦截
        context = EvaluationContext(user_id="u1", tier="t1", environment="production")
        result = evaluator.evaluate(base_flag, context)
        # Tier 检查在白名单之前，所以被拦截
        assert result.reason == EvaluationReason.TIER_MISMATCH

    # ==================== 边界情况测试 ====================

    def test_flag_disabled_ignores_tier(self, evaluator, base_flag):
        """Flag 禁用时不检查 Tier"""
        base_flag["enabled"] = False
        base_flag["allowed_tiers"] = ["t3"]

        context = EvaluationContext(user_id="u1", tier="t1", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.DISABLED

    def test_environment_mismatch_before_tier(self, evaluator, base_flag):
        """环境不匹配在 Tier 检查之前"""
        base_flag["environments"] = ["staging"]
        base_flag["allowed_tiers"] = ["t3"]

        context = EvaluationContext(user_id="u1", tier="t1", environment="production")
        result = evaluator.evaluate(base_flag, context)
        assert result.reason == EvaluationReason.ENVIRONMENT


class TestTierFilteringIntegration:
    """Tier 分层筛选集成测试 - 模拟真实场景"""

    @pytest.fixture
    def evaluator(self):
        return UnifiedEvaluator()

    def test_beta_feature_for_pro_users(self, evaluator):
        """场景: Beta 功能仅对 Pro 用户开放"""
        flag = {
            "key": "beta_ai_v2",
            "name": "Beta AI V2",
            "flag_type": "boolean",
            "enabled": True,
            "environments": ["production"],
            "allowed_tiers": ["t3", "t4"],
            "rollout_percentage": 100,
            "whitelist_user_ids": [],
            "blacklist_user_ids": [],
            "targeting_rules": [],
            "variants": [
                {"key": "control", "value": False, "weight": 50},
                {"key": "treatment", "value": True, "weight": 50}
            ]
        }

        # Free 用户看不到
        ctx_free = EvaluationContext(user_id="free_user", tier="t1", environment="production")
        assert evaluator.evaluate(flag, ctx_free).enabled is False

        # Starter 用户看不到
        ctx_starter = EvaluationContext(user_id="starter_user", tier="t2", environment="production")
        assert evaluator.evaluate(flag, ctx_starter).enabled is False

        # Pro 用户看得到
        ctx_pro = EvaluationContext(user_id="pro_user", tier="t3", environment="production")
        assert evaluator.evaluate(flag, ctx_pro).enabled is True

    def test_gradual_rollout_by_tier(self, evaluator):
        """场景: 分层灰度 - 先 Pro 全量，再 Starter 50%"""
        flag = {
            "key": "new_editor",
            "name": "New Editor",
            "flag_type": "boolean",
            "enabled": True,
            "environments": ["production"],
            "allowed_tiers": [],  # 顶层不限制
            "rollout_percentage": 0,  # 默认关闭
            "whitelist_user_ids": [],
            "blacklist_user_ids": [],
            "targeting_rules": [
                {
                    "id": "rule_pro_100",
                    "priority": 1,
                    "tiers": ["t3", "t4"],
                    "conditions": [],
                    "rollout_percentage": 100,
                    "variant": "treatment"
                },
                {
                    "id": "rule_starter_50",
                    "priority": 2,
                    "tiers": ["t2"],
                    "conditions": [],
                    "rollout_percentage": 50,
                    "variant": "treatment"
                }
            ],
            "variants": [
                {"key": "control", "value": False, "weight": 50},
                {"key": "treatment", "value": True, "weight": 50}
            ]
        }

        # Pro 用户 100% 看得到
        ctx_pro = EvaluationContext(user_id="pro_user", tier="t3", environment="production")
        result_pro = evaluator.evaluate(flag, ctx_pro)
        assert result_pro.reason == EvaluationReason.RULE
        assert result_pro.enabled is True

        # Free 用户看不到 (不命中任何规则，默认 rollout=0)
        ctx_free = EvaluationContext(user_id="free_user", tier="t1", environment="production")
        result_free = evaluator.evaluate(flag, ctx_free)
        assert result_free.enabled is False
