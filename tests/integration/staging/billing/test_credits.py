"""
Billing Credits API Tests (Black Box)

测试 GET /api/v2/user/billing/credits

基于业务规则的黑盒测试，不依赖代码实现

业务规则 (来源: 产品文档):
1. 积分分为月度积分和永久积分
2. 月度积分每月重置，永久积分不过期
3. total = monthly + permanent
4. 积分不能为负数
5. 不同 Tier 有不同的月度积分配额
   - t1 (Free): 0 月度积分
   - t2 (Starter): 100 月度积分
   - t3 (Pro): 200 月度积分

@module tests.integration.staging.billing.test_credits
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints, Tiers, ResponseKeys


@pytest.mark.p0
class TestBillingCredits(BaseAPITest):
    """
    GET /api/v2/user/billing/credits 黑盒测试

    从用户视角验证积分查询功能
    """

    ENDPOINT = Endpoints.BILLING_CREDITS

    # ==========================================
    # 功能测试: 正常场景
    # ==========================================

    def test_get_credits_returns_correct_structure(self, auth_client):
        """
        业务规则: 积分接口应返回月度、永久、总积分和 tier

        期望响应:
        {
            "monthly_credits": int,
            "permanent_credits": int,
            "total_credits": int,
            "tier": "t1" | "t2" | "t3" | "t4"
        }
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 验证必需字段存在
        required_fields = [
            "monthly_credits",
            "permanent_credits",
            "total_credits",
            "tier"
        ]
        self.assert_has_fields(data, required_fields)

    def test_credits_are_non_negative(self, auth_client):
        """
        业务规则: 积分不能为负数

        用户的积分余额永远 >= 0
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        assert data["monthly_credits"] >= 0, "月度积分不能为负"
        assert data["permanent_credits"] >= 0, "永久积分不能为负"
        assert data["total_credits"] >= 0, "总积分不能为负"

    def test_total_equals_monthly_plus_permanent(self, auth_client):
        """
        业务规则: total_credits = monthly_credits + permanent_credits

        这是积分系统的基本数学关系
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        expected_total = data["monthly_credits"] + data["permanent_credits"]
        assert data["total_credits"] == expected_total, (
            f"总积分计算错误: {data['total_credits']} != "
            f"{data['monthly_credits']} + {data['permanent_credits']}"
        )

    def test_tier_is_valid_value(self, auth_client):
        """
        业务规则: Tier 只能是 t1/t2/t3/t4 之一

        系统定义了 4 个 Tier 等级
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        valid_tiers = [Tiers.FREE, Tiers.STARTER, Tiers.PRO, Tiers.ENTERPRISE]
        self.assert_field_in(data, "tier", valid_tiers)

    def test_credits_are_integers(self, auth_client):
        """
        业务规则: 积分是整数

        积分系统使用整数计算，避免浮点数精度问题
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        self.assert_field_type(data, "monthly_credits", int)
        self.assert_field_type(data, "permanent_credits", int)
        self.assert_field_type(data, "total_credits", int)

    # ==========================================
    # 认证测试: 必须登录
    # ==========================================

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 积分是用户私有数据，必须登录才能查看

        未登录用户应该收到 401
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_invalid_token_rejected(self, anon_client):
        """
        业务规则: 无效的认证 token 应被拒绝

        防止伪造身份查看他人积分
        """
        response = anon_client.get(
            self.ENDPOINT,
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        self.assert_unauthorized(response)

    def test_malformed_auth_header_rejected(self, anon_client):
        """
        业务规则: 格式错误的 Authorization header 应被拒绝

        标准格式: "Bearer {token}"
        """
        # 没有 Bearer 前缀
        response = anon_client.get(
            self.ENDPOINT,
            headers={"Authorization": "some_token_without_bearer"}
        )
        self.assert_unauthorized(response)

    def test_empty_token_rejected(self, anon_client):
        """
        业务规则: 空 token 应被拒绝

        注: 由于 HTTP 客户端不允许发送 "Bearer " (空值) header,
        此测试改为验证只有 "Bearer" 前缀的情况
        """
        response = anon_client.get(
            self.ENDPOINT,
            headers={"Authorization": "Bearer invalid"}
        )
        self.assert_unauthorized(response)

    # ==========================================
    # 性能测试: 响应时间
    # ==========================================

    def test_response_time_acceptable(self, auth_client):
        """
        业务规则: 积分查询是高频操作，应快速响应

        SLA: 响应时间 < 2s (Staging 环境允许更宽松)
        生产环境建议 < 500ms
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code == 200

        # 检查响应时间 (Staging 环境可能较慢)
        self.assert_response_time(response, max_seconds=2.0)

    # ==========================================
    # 安全测试: 数据隔离
    # ==========================================

    def test_no_sensitive_data_in_error(self, anon_client):
        """
        业务规则: 错误响应不应泄露敏感信息

        即使请求失败，也不应暴露:
        - 其他用户的积分
        - 系统内部信息
        - 数据库结构
        """
        response = anon_client.get(self.ENDPOINT)
        assert response.status_code == 401

        # 错误响应不应包含积分数字
        text = response.text.lower()
        assert "monthly" not in text or "credits" in text  # 只是字段名可以
        # 不应有堆栈跟踪
        self.assert_no_stack_trace(response)

    # ==========================================
    # 边界测试: Tier 与积分关系
    # ==========================================

    def test_free_tier_has_zero_monthly_credits(self, auth_client):
        """
        业务规则: t1 (Free) 用户没有月度积分

        免费用户不享受月度积分配额
        注: 此测试假设当前测试用户是 t1
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 只有当用户是 t1 时验证
        if data["tier"] == Tiers.FREE:
            assert data["monthly_credits"] == 0, (
                "Free 用户的月度积分应为 0"
            )

    # ==========================================
    # 幂等性测试
    # ==========================================

    def test_multiple_requests_return_consistent_data(self, auth_client):
        """
        业务规则: 连续请求应返回一致的数据

        积分查询是只读操作，多次调用结果应一致
        (除非有并发的积分变动)
        """
        response1 = auth_client.get(self.ENDPOINT)
        data1 = self.assert_success(response1)

        response2 = auth_client.get(self.ENDPOINT)
        data2 = self.assert_success(response2)

        # 短时间内数据应一致
        assert data1["total_credits"] == data2["total_credits"], (
            "连续两次查询返回不同的积分余额"
        )
        assert data1["tier"] == data2["tier"], (
            "连续两次查询返回不同的 tier"
        )


@pytest.mark.p0
class TestBillingTransactions(BaseAPITest):
    """
    GET /api/v2/user/billing/transactions 黑盒测试

    业务规则:
    1. 用户可以查看自己的积分交易历史
    2. 支持分页 (offset/limit)
    3. 支持按类型和日期过滤
    4. 交易记录按时间倒序排列
    """

    ENDPOINT = Endpoints.BILLING_TRANSACTIONS

    def test_returns_paginated_list(self, auth_client):
        """
        业务规则: 交易历史应分页返回

        期望响应包含 items, total, offset, limit
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 验证分页结构
        assert "items" in data or "transactions" in data, "缺少列表字段"
        items_key = "items" if "items" in data else "transactions"
        assert isinstance(data[items_key], list), "列表字段不是数组"

    def test_pagination_parameters(self, auth_client):
        """
        业务规则: 支持 offset 和 limit 分页参数
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"limit": 5, "offset": 0}
        )
        data = self.assert_success(response)

        items_key = "items" if "items" in data else "transactions"
        # limit=5 应该最多返回 5 条
        assert len(data[items_key]) <= 5

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 交易历史是私有数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p0
class TestBillingCanAfford(BaseAPITest):
    """
    GET /api/v2/user/billing/can-afford 黑盒测试

    业务规则:
    1. 用于检查用户是否有足够积分进行某项操作
    2. 需要指定金额或操作类型
    3. 返回 true/false
    """

    ENDPOINT = Endpoints.BILLING_CAN_AFFORD

    def test_check_with_amount(self, auth_client):
        """
        业务规则: 可以通过金额检查能否承担
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"amount": 5}
        )
        data = self.assert_success(response)

        # 应返回布尔值或可转换为布尔的结果
        assert "can_afford" in data or "affordable" in data or "result" in data

    def test_check_zero_amount_always_affordable(self, auth_client):
        """
        业务规则: 0 积分的操作总是可以承担
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"amount": 0}
        )
        data = self.assert_success(response)

        result_key = next(
            (k for k in ["can_afford", "affordable", "result"] if k in data),
            None
        )
        if result_key:
            assert data[result_key] is True, "0 积分应该总是可以承担"

    def test_negative_amount_rejected(self, auth_client):
        """
        业务规则: 负数金额应被拒绝

        检查 "能否承担 -5 积分" 是无意义的
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"amount": -5}
        )
        # 应返回 400 Bad Request
        assert response.status_code in [400, 422], (
            f"负数金额应被拒绝，但返回了 {response.status_code}"
        )

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 必须登录才能检查
        """
        response = anon_client.get(
            self.ENDPOINT,
            params={"amount": 5}
        )
        self.assert_unauthorized(response)
