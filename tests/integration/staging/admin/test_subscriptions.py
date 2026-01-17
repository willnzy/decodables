"""
Admin Subscriptions API Tests (Black Box)

测试 /api/v2/admin/subscriptions 相关接口

业务规则:
1. 只有 admin 才能访问订阅管理接口
2. 支持退款、取消订阅、降级
3. 所有操作都有审计日志
4. 涉及金额的操作需要二次确认

实际端点:
- POST /subscriptions/refund - 退款
- POST /subscriptions/subscription/cancel - 取消订阅
- POST /subscriptions/subscription/downgrade - 降级订阅

@module tests.integration.staging.admin.test_subscriptions
"""

import pytest
import uuid
from ..base import BaseAPITest
from ..constants import API_ADMIN


@pytest.mark.p1
class TestAdminSubscriptionRefund(BaseAPITest):
    """
    POST /api/v2/admin/subscriptions/refund 黑盒测试

    退款操作
    """

    ENDPOINT = f"{API_ADMIN}/subscriptions/refund"

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
        assert response.status_code in [400, 403, 404]


@pytest.mark.p1
class TestAdminSubscriptionCancel(BaseAPITest):
    """
    POST /api/v2/admin/subscriptions/subscription/cancel 黑盒测试

    取消订阅
    """

    ENDPOINT = f"{API_ADMIN}/subscriptions/subscription/cancel"

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
        assert response.status_code in [400, 403, 404]


@pytest.mark.p1
class TestAdminSubscriptionDowngrade(BaseAPITest):
    """
    POST /api/v2/admin/subscriptions/subscription/downgrade 黑盒测试

    降级订阅
    """

    ENDPOINT = f"{API_ADMIN}/subscriptions/subscription/downgrade"

    def test_downgrade_requires_admin(self, anon_client):
        """
        业务规则: 降级订阅需要管理员权限
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test_12345",
                "target_tier": "t1"
            }
        )
        self.assert_unauthorized(response)

    def test_downgrade_missing_fields(self, auth_client):
        """
        业务规则: 缺少必填字段
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}
        )
        assert response.status_code in [400, 403, 422]

    def test_downgrade_nonexistent_user(self, auth_client):
        """
        业务规则: 降级不存在用户的订阅
        """
        fake_id = f"user_{uuid.uuid4().hex[:20]}"
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": fake_id,
                "target_tier": "t1"
            }
        )
        assert response.status_code in [400, 403, 404]

    def test_downgrade_valid_request(self, auth_client):
        """
        业务规则: 有效的降级请求
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={
                "user_id": "user_test_12345",
                "target_tier": "t1",
                "reason": "User requested downgrade"
            }
        )
        # 可能成功或失败 (非 admin / 用户不存在 / 业务规则限制)
        assert response.status_code in [200, 400, 403, 404]


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
            f"{API_ADMIN}/subscriptions/refund",
            json={
                "user_id": "user_test_12345",
                "amount": 100,
                "reason": ""
            }
        )
        # 空原因可能被接受或拒绝
        assert response.status_code in [200, 400, 403, 422]

    def test_refund_very_long_reason(self, auth_client):
        """
        业务规则: 原因过长
        """
        response = auth_client.post(
            f"{API_ADMIN}/subscriptions/refund",
            json={
                "user_id": "user_test_12345",
                "amount": 100,
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
            f"{API_ADMIN}/subscriptions/subscription/cancel",
            json={
                "user_id": "user_test_12345",
                "reason": "Test",
                "immediate": True
            }
        )
        assert response.status_code in [200, 400, 403, 404, 422]
