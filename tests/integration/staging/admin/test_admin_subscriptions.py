"""
Admin Subscriptions API Tests (Black Box)

测试 /api/v2/admin/subscriptions 相关接口

基于业务规则的黑盒测试，不依赖代码实现

业务规则 (来源: 产品文档):
1. 退款、取消订阅、降级都需要管理员权限
2. 这些操作需要 user_id + user_code 双因素验证
3. 退款有金额上限
4. 降级只能到 t1 或 t2

⚠️ 注意: 这些测试使用普通用户 Token，预期返回 403

@module tests.integration.staging.admin.test_admin_subscriptions
"""

import pytest
from ..base import BaseAPITest


# Admin API Base URL
API_ADMIN_SUBSCRIPTIONS = "/api/v2/admin/subscriptions"


@pytest.mark.p0
class TestAdminRefund(BaseAPITest):
    """
    POST /api/v2/admin/subscriptions/refund 黑盒测试

    退款处理
    """

    ENDPOINT = f"{API_ADMIN_SUBSCRIPTIONS}/refund"

    def test_refund_requires_admin(self, auth_client):
        """
        业务规则: 退款需要管理员权限

        退款是敏感财务操作，必须严格控制
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test123",
                "user_code": "26010914305278900123456789",
                "payment_intent_id": "pi_test123",
                "reason": "Test refund"
            }
        )

        assert response.status_code == 403, (
            f"退款需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )

    def test_anonymous_rejected(self, anon_client):
        """
        业务规则: 未登录用户应返回 401
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test123",
                "user_code": "26010914305278900123456789",
                "payment_intent_id": "pi_test123",
                "reason": "Test refund"
            }
        )

        self.assert_unauthorized(response)


@pytest.mark.p0
class TestAdminCancelSubscription(BaseAPITest):
    """
    POST /api/v2/admin/subscriptions/subscription/cancel 黑盒测试

    取消订阅
    """

    ENDPOINT = f"{API_ADMIN_SUBSCRIPTIONS}/subscription/cancel"

    def test_cancel_requires_admin(self, auth_client):
        """
        业务规则: 取消订阅需要管理员权限
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test123",
                "user_code": "26010914305278900123456789",
                "subscription_id": "sub_test123",
                "reason": "Test cancel"
            }
        )

        assert response.status_code == 403, (
            f"取消订阅需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )

    def test_anonymous_rejected(self, anon_client):
        """
        业务规则: 未登录用户应返回 401
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test123",
                "user_code": "26010914305278900123456789",
                "subscription_id": "sub_test123",
                "reason": "Test cancel"
            }
        )

        self.assert_unauthorized(response)


@pytest.mark.p1
class TestAdminDowngrade(BaseAPITest):
    """
    POST /api/v2/admin/subscriptions/subscription/downgrade 黑盒测试

    降级订阅
    """

    ENDPOINT = f"{API_ADMIN_SUBSCRIPTIONS}/subscription/downgrade"

    def test_downgrade_requires_admin(self, auth_client):
        """
        业务规则: 降级订阅需要管理员权限
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test123",
                "user_code": "26010914305278900123456789",
                "subscription_id": "sub_test123",
                "target_tier": "t1",
                "reason": "Test downgrade"
            }
        )

        assert response.status_code == 403, (
            f"降级订阅需要管理员权限，普通用户应返回 403，但返回了 {response.status_code}"
        )

    def test_anonymous_rejected(self, anon_client):
        """
        业务规则: 未登录用户应返回 401
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test123",
                "user_code": "26010914305278900123456789",
                "subscription_id": "sub_test123",
                "target_tier": "t1",
                "reason": "Test downgrade"
            }
        )

        self.assert_unauthorized(response)
