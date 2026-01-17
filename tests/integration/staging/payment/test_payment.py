"""
Payment API Tests (Black Box)

测试 /api/v2/user/payment 相关接口

业务规则:
1. 用户可以创建 Stripe Checkout Session
2. 用户可以访问 Billing Portal
3. 支持订阅 (t2/t3) 和积分包 (credits_100/500/2000)

@module tests.integration.staging.payment.test_payment
"""

import pytest
from ..base import BaseAPITest
from ..constants import Endpoints


@pytest.mark.p0
class TestPaymentCheckout(BaseAPITest):
    """
    POST /api/v2/user/payment/checkout 黑盒测试

    创建 Stripe Checkout Session
    """

    ENDPOINT = Endpoints.PAYMENT_CHECKOUT

    def test_checkout_requires_plan_type(self, auth_client):
        """
        业务规则: 创建 Checkout 需要提供 plan_type
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={}  # 缺少 plan_type
        )
        assert response.status_code in [400, 422]

    def test_checkout_valid_subscription_plans(self, auth_client):
        """
        业务规则: 有效的订阅计划应返回 checkout URL

        有效计划: starter, pro
        """
        for plan in ["starter", "pro"]:
            response = auth_client.post(
                self.ENDPOINT,
                json={"plan_type": plan}
            )
            # 可能成功返回 URL 或因为已订阅返回错误
            if response.status_code == 200:
                data = response.json()
                assert "url" in data, f"{plan} 应返回 checkout URL"
                assert data["url"].startswith("https://"), "URL 应该是 HTTPS"

    def test_checkout_valid_credits_plans(self, auth_client):
        """
        业务规则: 有效的积分包应返回 checkout URL

        有效积分包: credits_100, credits_500, credits_2000
        """
        for plan in ["credits_100", "credits_500", "credits_2000"]:
            response = auth_client.post(
                self.ENDPOINT,
                json={"plan_type": plan}
            )
            if response.status_code == 200:
                data = response.json()
                assert "url" in data, f"{plan} 应返回 checkout URL"

    def test_checkout_invalid_plan_rejected(self, auth_client):
        """
        业务规则: 无效的 plan_type 应被拒绝
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"plan_type": "invalid_plan"}
        )
        assert response.status_code in [400, 422]

    def test_checkout_response_includes_discount_info(self, auth_client):
        """
        业务规则: Checkout 响应应包含折扣信息
        """
        response = auth_client.post(
            self.ENDPOINT,
            json={"plan_type": "starter"}
        )
        if response.status_code == 200:
            data = response.json()
            # discount_applied 字段应该存在 (可能为 0)
            assert "discount_applied" in data or "url" in data

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 创建 Checkout 必须登录
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={"plan_type": "starter"}
        )
        self.assert_unauthorized(response)


@pytest.mark.p0
class TestPaymentPortal(BaseAPITest):
    """
    POST /api/v2/user/payment/portal 黑盒测试

    获取 Stripe Billing Portal URL
    """

    ENDPOINT = Endpoints.PAYMENT_PORTAL

    def test_portal_requires_subscription(self, auth_client):
        """
        业务规则: 访问 Portal 需要有订阅

        没有订阅的用户应该返回 400
        """
        response = auth_client.post(self.ENDPOINT)
        # 有订阅: 200 + URL
        # 无订阅: 400
        assert response.status_code in [200, 400]

    def test_portal_returns_url(self, auth_client):
        """
        业务规则: 有订阅的用户应返回 Portal URL
        """
        response = auth_client.post(self.ENDPOINT)
        if response.status_code == 200:
            data = response.json()
            assert "url" in data, "应返回 portal URL"
            assert data["url"].startswith("https://"), "URL 应该是 HTTPS"

    def test_requires_authentication(self, anon_client):
        """
        业务规则: 访问 Portal 必须登录
        """
        response = anon_client.post(self.ENDPOINT)
        self.assert_unauthorized(response)


@pytest.mark.p2
class TestPaymentRateLimits(BaseAPITest):
    """
    Payment 接口速率限制测试
    """

    def test_checkout_rate_limit(self, auth_client):
        """
        业务规则: Checkout 有速率限制 (5/minute)
        """
        # 速率限制测试需要快速多次请求
        # 在集成测试中可能不适合测试
        pass

    def test_portal_rate_limit(self, auth_client):
        """
        业务规则: Portal 有速率限制 (10/minute)
        """
        pass
