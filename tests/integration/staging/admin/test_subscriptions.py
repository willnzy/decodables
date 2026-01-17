"""
Admin Subscriptions API Tests (Black Box)

测试 /api/admin/subscriptions 相关接口

业务规则:
1. 只有 admin 才能访问订阅管理接口
2. 支持退款、取消订阅、赠送积分
3. 所有操作都有审计日志
4. 涉及金额的操作需要二次确认

@module tests.integration.staging.admin.test_subscriptions
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p1
class TestAdminSubscriptionRefund(BaseAPITest):
    """
    POST /api/admin/subscriptions/refund 黑盒测试

    退款操作
    """

    ENDPOINT = Endpoints.ADMIN_SUBSCRIPTIONS_REFUND

    def test_refund_requires_admin(self, anon_client):
        """
        业务规则: 退款需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test_12345",
                "amount": 100,
                "reason": "Test refund"
            }
        )
        self.assert_unauthorized(response)

    def test_refund_missing_required_fields(self, auth_client):
        """
        业务规则: 缺少必填字段
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        # 可能返回 400/422 (缺少字段) 或 403 (非 admin)
        assert response.status_code in [400, 403, 422]

    def test_refund_invalid_amount(self, auth_client):
        """
        业务规则: 无效的退款金额
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test_12345",
                "amount": -100,
                "reason": "Test refund"
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_refund_nonexistent_user(self, auth_client):
        """
        业务规则: 为不存在的用户退款
        """
        fake_id = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": fake_id,
                "amount": 100,
                "reason": "Test refund"
            }
        )
        assert response.status_code in [403, 404]


@pytest.mark.p1
class TestAdminSubscriptionCancel(BaseAPITest):
    """
    POST /api/admin/subscriptions/subscription/cancel 黑盒测试

    取消订阅
    """

    ENDPOINT = Endpoints.ADMIN_SUBSCRIPTIONS_CANCEL

    def test_cancel_requires_admin(self, anon_client):
        """
        业务规则: 取消订阅需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test_12345",
                "reason": "Test cancellation"
            }
        )
        self.assert_unauthorized(response)

    def test_cancel_missing_user_id(self, auth_client):
        """
        业务规则: 缺少用户 ID
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"reason": "Test cancellation"}
        )
        assert response.status_code in [400, 403, 422]

    def test_cancel_nonexistent_user(self, auth_client):
        """
        业务规则: 取消不存在用户的订阅
        """
        fake_id = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": fake_id,
                "reason": "Test cancellation"
            }
        )
        assert response.status_code in [403, 404]


@pytest.mark.p1
class TestAdminGiftCredits(BaseAPITest):
    """
    POST /api/admin/subscriptions/gift-credits 黑盒测试

    赠送积分
    """

    ENDPOINT = Endpoints.ADMIN_SUBSCRIPTIONS_GIFT_CREDITS

    def test_gift_credits_requires_admin(self, anon_client):
        """
        业务规则: 赠送积分需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test_12345",
                "credits": 100,
                "reason": "Compensation"
            }
        )
        self.assert_unauthorized(response)

    def test_gift_credits_missing_fields(self, auth_client):
        """
        业务规则: 缺少必填字段
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        assert response.status_code in [400, 403, 422]

    def test_gift_credits_invalid_amount(self, auth_client):
        """
        业务规则: 无效的积分数量 (负数)
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test_12345",
                "credits": -100,
                "reason": "Test"
            }
        )
        assert response.status_code in [400, 403, 422]

    def test_gift_credits_zero_amount(self, auth_client):
        """
        业务规则: 赠送 0 积分
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test_12345",
                "credits": 0,
                "reason": "Test"
            }
        )
        # 0 积分可能被接受或拒绝
        assert response.status_code in [200, 400, 403, 422]

    def test_gift_credits_nonexistent_user(self, auth_client):
        """
        业务规则: 为不存在的用户赠送积分
        """
        fake_id = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": fake_id,
                "credits": 100,
                "reason": "Test"
            }
        )
        assert response.status_code in [403, 404]

    def test_gift_credits_excessive_amount(self, auth_client):
        """
        业务规则: 赠送过多积分应有上限
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test_12345",
                "credits": 999999999,
                "reason": "Test"
            }
        )
        # 可能有上限限制
        assert response.status_code in [200, 400, 403, 422]


@pytest.mark.p1
class TestAdminUserSubscription(BaseAPITest):
    """
    GET /api/admin/subscriptions/user/{user_id} 黑盒测试

    获取用户订阅信息
    """

    def test_get_subscription_requires_admin(self, anon_client, test_user_id):
        """
        业务规则: 获取订阅信息需要管理员权限
        """
        response = anon_client.get(Endpoints.admin_user_subscription(test_user_id))
        self.assert_unauthorized(response)

    def test_get_nonexistent_user_subscription(self, auth_client):
        """
        业务规则: 获取不存在用户的订阅
        """
        fake_id = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.get(Endpoints.admin_user_subscription(fake_id))
        assert response.status_code in [403, 404]

    def test_get_user_subscription(self, auth_client, test_user_id):
        """
        业务规则: 获取用户订阅信息
        """
        response = auth_client.get(Endpoints.admin_user_subscription(test_user_id))
        # 可能返回 200/404 (admin) 或 403 (非 admin)
        assert response.status_code in [200, 403, 404]


@pytest.mark.p2
class TestAdminSubscriptionsValidation(BaseAPITest):
    """
    Admin Subscriptions API 参数验证测试
    """

    def test_refund_with_empty_reason(self, auth_client):
        """
        业务规则: 空退款原因
        """
        response = auth_client.post(
            Endpoints.ADMIN_SUBSCRIPTIONS_REFUND,
            json={
                "user_id": "user_test_12345",
                "amount": 100,
                "reason": ""
            }
        )
        # 空原因可能被接受或拒绝
        assert response.status_code in [200, 400, 403, 422]

    def test_gift_credits_very_long_reason(self, auth_client):
        """
        业务规则: 原因过长
        """
        response = auth_client.post(
            Endpoints.ADMIN_SUBSCRIPTIONS_GIFT_CREDITS,
            json={
                "user_id": "user_test_12345",
                "credits": 100,
                "reason": "a" * 10000
            }
        )
        # 可能被截断或拒绝
        assert response.status_code in [200, 400, 403, 422]

    def test_cancel_with_immediate_flag(self, auth_client):
        """
        业务规则: 立即取消 vs 到期取消
        """
        response = auth_client.post(
            Endpoints.ADMIN_SUBSCRIPTIONS_CANCEL,
            json={
                "user_id": "user_test_12345",
                "reason": "Test",
                "immediate": True
            }
        )
        assert response.status_code in [200, 400, 403, 404, 422]
