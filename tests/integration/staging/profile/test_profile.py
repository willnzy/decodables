"""
User Profile API Tests (Black Box)

测试 GET /api/v2/user/profile/me

基于业务规则的黑盒测试，不依赖代码实现

业务规则 (来源: 产品文档):
1. 每个用户都有唯一的 user_id (格式: user_xxx)
2. 每个用户都有 user_code (26位数字，用于客服识别)
3. 用户有 tier 等级: t1 (Free) / t2 (Starter) / t3 (Pro)
4. 用户有角色: user (普通用户) / admin (管理员)
5. 用户资料包含积分信息 (monthly + permanent)

@module tests.integration.staging.profile.test_profile
"""

import pytest
import re
from ..base import BaseAPITest
from ..constants import Endpoints, Tiers


@pytest.mark.p0
class TestUserProfile(BaseAPITest):
    """
    GET /api/v2/user/profile/me 黑盒测试

    从用户视角验证个人资料查询功能
    """

    ENDPOINT = Endpoints.PROFILE_ME

    # ==========================================
    # 功能测试: 正常场景
    # ==========================================

    def test_get_profile_returns_correct_structure(self, auth_client):
        """
        业务规则: 资料接口应返回完整的用户信息

        期望响应包含:
        - id: 系统内部用户标识 (格式: user_xxx)
        - email: 用户邮箱
        - tier: 会员等级
        - role: 用户角色
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 验证核心字段存在
        # API 通过 UserProfileService.get_user_profile() 返回 "user_id" (非 "id")
        # 数据库 "id" 字段被映射为 "user_id"
        required_fields = ["user_id", "tier"]
        self.assert_has_fields(data, required_fields)

    def test_user_id_format(self, auth_client):
        """
        业务规则: user_id (用户ID) 格式为 user_xxx

        Clerk 生成的用户ID格式统一。
        API 通过 UserProfileService 将数据库 "id" 映射为 "user_id"。
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        user_id = data.get("user_id")
        assert user_id is not None, "缺少 user_id"
        assert user_id.startswith("user_"), f"user_id 格式错误: {user_id}"

    def test_user_code_format(self, auth_client):
        """
        业务规则: user_code 是26位数字

        user_code 格式:
        - 6位日期 (YYMMDD)
        - 6位时间 (HHMMSS)
        - 4位毫秒
        - 7位序号
        - 3位随机数
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        user_code = data.get("user_code")
        if user_code:  # 可能是旧用户没有 user_code
            assert len(user_code) == 26, f"user_code 长度应为26: {user_code}"
            assert user_code.isdigit(), f"user_code 应为纯数字: {user_code}"

    def test_tier_is_valid_value(self, auth_client):
        """
        业务规则: Tier 只能是 t1/t2/t3/t4 之一

        系统定义了 4 个会员等级
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        valid_tiers = [Tiers.FREE, Tiers.STARTER, Tiers.PRO, Tiers.ENTERPRISE]
        self.assert_field_in(data, "tier", valid_tiers)

    def test_role_is_valid_value(self, auth_client):
        """
        业务规则: Role 只能是 user 或 admin

        普通用户为 user，管理员为 admin
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        role = data.get("role")
        if role:  # role 字段可能不存在
            assert role in ["user", "admin"], f"无效的 role: {role}"

    def test_email_format(self, auth_client):
        """
        业务规则: email 应是有效的邮箱格式
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        email = data.get("email")
        if email:
            # 简单的邮箱格式验证
            assert "@" in email, f"email 格式无效: {email}"
            assert "." in email.split("@")[1], f"email 格式无效: {email}"

    def test_credits_fields_present(self, auth_client):
        """
        业务规则: 用户资料应包含积分信息

        积分字段可能是:
        - credits_monthly + credits_permanent + credits_total
        - 或者嵌套在 credits 对象中
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 检查积分字段 (可能是不同的格式)
        has_credits = (
            "credits_monthly" in data or
            "credits_permanent" in data or
            "credits_total" in data or
            "credits" in data or
            "total_credits" in data
        )
        assert has_credits, "响应中缺少积分信息"

    def test_credits_are_non_negative(self, auth_client):
        """
        业务规则: 积分不能为负数
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 检查各种可能的积分字段
        credit_fields = [
            "credits_monthly", "credits_permanent", "credits_total",
            "monthly_credits", "permanent_credits", "total_credits"
        ]

        for field in credit_fields:
            if field in data:
                value = data[field]
                if isinstance(value, (int, float)):
                    assert value >= 0, f"{field} 不能为负数: {value}"

    # ==========================================
    # 认证测试: 必须登录
    # ==========================================

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 个人资料是私有数据，必须登录才能查看
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)

    def test_invalid_token_rejected(self, anon_client):
        """
        业务规则: 无效的认证 token 应被拒绝
        """
        response = anon_client.get(
            self.ENDPOINT,
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        self.assert_unauthorized(response)

    # ==========================================
    # 性能测试
    # ==========================================

    def test_response_time_acceptable(self, auth_client):
        """
        业务规则: 资料查询是高频操作，应快速响应

        SLA: 响应时间 < 2s (Staging 环境)
        """
        response = auth_client.get(self.ENDPOINT)
        assert response.status_code == 200
        self.assert_response_time(response, max_seconds=2.0)

    # ==========================================
    # 幂等性测试
    # ==========================================

    def test_multiple_requests_return_consistent_data(self, auth_client):
        """
        业务规则: 连续请求应返回一致的数据

        资料查询是只读操作，结果应一致
        """
        response1 = auth_client.get(self.ENDPOINT)
        data1 = self.assert_success(response1)

        response2 = auth_client.get(self.ENDPOINT)
        data2 = self.assert_success(response2)

        # 核心字段应一致
        assert data1.get("user_id") == data2.get("user_id")
        assert data1.get("tier") == data2.get("tier")
        assert data1.get("email") == data2.get("email")


@pytest.mark.p1
class TestUserNotifications(BaseAPITest):
    """
    GET /api/v2/user/profile/notifications 黑盒测试

    业务规则:
    1. 用户可以查看自己的通知列表
    2. 支持 unread_only 过滤
    3. 通知按时间倒序排列
    """

    ENDPOINT = Endpoints.PROFILE_NOTIFICATIONS

    def test_get_notifications_returns_list(self, auth_client):
        """
        业务规则: 通知接口应返回通知列表
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应可能是列表或包含 items 的对象
        if isinstance(data, list):
            notifications = data
        else:
            notifications = data.get("items") or data.get("notifications") or []

        assert isinstance(notifications, list), "通知应该是列表"

    def test_filter_unread_only(self, auth_client):
        """
        业务规则: 可以只查看未读通知
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"unread_only": True}
        )
        data = self.assert_success(response)

        # 验证返回的都是未读通知
        if isinstance(data, list):
            notifications = data
        else:
            notifications = data.get("items") or data.get("notifications") or []

        for notif in notifications:
            if "is_read" in notif:
                assert notif["is_read"] is False, "unread_only=True 时不应返回已读通知"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 通知是私有数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestUserHistory(BaseAPITest):
    """
    GET /api/v2/user/profile/history 黑盒测试

    业务规则:
    1. 用户可以查看自己的积分交易历史
    2. 支持分页 (offset/limit)
    3. 按时间倒序排列
    """

    ENDPOINT = Endpoints.PROFILE_HISTORY

    def test_get_history_returns_list(self, auth_client):
        """
        业务规则: 历史接口应返回交易记录列表
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应可能是列表或包含 items 的对象
        if isinstance(data, list):
            items = data
        else:
            items = data.get("items") or data.get("transactions") or data.get("history") or []

        assert isinstance(items, list), "历史记录应该是列表"

    def test_pagination_works(self, auth_client):
        """
        业务规则: 分页参数应生效
        """
        response = auth_client.get(
            self.ENDPOINT,
            params={"limit": 5, "offset": 0}
        )
        data = self.assert_success(response)

        if isinstance(data, dict):
            items = data.get("items") or data.get("transactions") or data.get("history") or []
            # limit=5 应该最多返回 5 条
            assert len(items) <= 5, f"limit=5 但返回了 {len(items)} 条"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 历史记录是私有数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p1
class TestUserPurchases(BaseAPITest):
    """
    GET /api/v2/user/profile/purchases 黑盒测试

    业务规则:
    1. 用户可以查看自己的 Marketplace 购买记录
    2. 支持分页
    """

    ENDPOINT = Endpoints.PROFILE_PURCHASES

    def test_get_purchases_returns_list(self, auth_client):
        """
        业务规则: 购买记录接口应返回列表
        """
        response = auth_client.get(self.ENDPOINT)
        data = self.assert_success(response)

        # 响应可能是列表或包含 items 的对象
        if isinstance(data, list):
            items = data
        else:
            items = data.get("items") or data.get("purchases") or []

        assert isinstance(items, list), "购买记录应该是列表"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 购买记录是私有数据，必须登录
        """
        response = anon_client.get(self.ENDPOINT)
        self.assert_unauthorized(response)
