"""
Webhooks API Integration Tests

测试 Webhook 处理接口:
- POST /api/v2/user/webhooks/clerk - Clerk 用户事件
- POST /api/v2/user/webhooks/stripe - Stripe 支付事件

注意:
- Webhook 端点不需要常规认证
- 但需要签名验证
- 测试无签名请求应被拒绝

TDD Approach:
- Sad Path First: 400 (Invalid Signature) → 200

@module tests.integration.staging.webhooks.test_webhooks
"""

import pytest
import json

from tests.integration.staging.constants import Endpoints


# ==========================================
# Base Test Class
# ==========================================

class BaseAPITest:
    """Base class with common assertion methods."""

    def assert_success(self, response, expected_status: int = 200) -> dict:
        """Assert successful response and return JSON data."""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}. "
            f"Response: {response.text[:500]}"
        )
        return response.json()

    def assert_bad_request(self, response):
        """Assert 400 Bad Request."""
        assert response.status_code == 400, (
            f"Expected 400, got {response.status_code}"
        )


# ==========================================
# Test: Clerk Webhook
# ==========================================

@pytest.mark.p1
class TestClerkWebhook(BaseAPITest):
    """
    POST /api/v2/user/webhooks/clerk 黑盒测试

    Clerk 用户事件 Webhook

    业务规则:
    1. 必须通过 Svix 签名验证
    2. 无签名或无效签名返回 400
    3. 支持的事件: user.created, user.updated, session.*
    """

    ENDPOINT = Endpoints.WEBHOOKS_CLERK

    def test_clerk_webhook_without_signature_rejected(self, anon_client):
        """
        业务规则: 无签名请求应被拒绝

        Sad Path First: 400 Bad Request
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "type": "user.created",
                "data": {"id": "test_123"}
            }
        )

        # 应返回 400 或 500 (配置错误/签名验证失败)
        assert response.status_code in [400, 500], (
            f"无签名请求应被拒绝，但返回了 {response.status_code}"
        )

    def test_clerk_webhook_invalid_signature_rejected(self, anon_client):
        """
        业务规则: 无效签名应被拒绝

        Sad Path: 验证错误
        """
        response = anon_client.post(
            self.ENDPOINT,
            headers={
                "svix-id": "msg_test_123",
                "svix-timestamp": "1234567890",
                "svix-signature": "v1,invalid_signature_here"
            },
            json={
                "type": "user.created",
                "data": {"id": "test_123"}
            }
        )

        # 应返回 400 (签名验证失败)
        assert response.status_code in [400, 500], (
            f"无效签名应被拒绝，但返回了 {response.status_code}"
        )

    def test_clerk_webhook_empty_body_rejected(self, anon_client):
        """
        业务规则: 空请求体应被拒绝

        Sad Path: 验证错误
        """
        response = anon_client.post(
            self.ENDPOINT,
            content=b""
        )

        # 应返回 400 或 422 (验证失败)
        assert response.status_code in [400, 422, 500], (
            f"空请求体应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: Stripe Webhook
# ==========================================

@pytest.mark.p1
class TestStripeWebhook(BaseAPITest):
    """
    POST /api/v2/user/webhooks/stripe 黑盒测试

    Stripe 支付事件 Webhook

    业务规则:
    1. 必须包含 Stripe-Signature header
    2. 无签名或无效签名返回 400
    3. 支持的事件: checkout.session.completed, invoice.payment_succeeded, etc.
    """

    ENDPOINT = Endpoints.WEBHOOKS_STRIPE

    def test_stripe_webhook_without_signature_rejected(self, anon_client):
        """
        业务规则: 缺少 Stripe-Signature header 应返回 422

        Sad Path First: Header required
        """
        response = anon_client.post(
            self.ENDPOINT,
            json={
                "id": "evt_test_123",
                "type": "checkout.session.completed"
            }
        )

        # FastAPI 对于缺少必需 header 返回 422
        assert response.status_code == 422, (
            f"缺少签名 header 应返回 422，但返回了 {response.status_code}"
        )

    def test_stripe_webhook_invalid_signature_rejected(self, anon_client):
        """
        业务规则: 无效签名应被拒绝

        Sad Path: 验证错误
        """
        response = anon_client.post(
            self.ENDPOINT,
            headers={
                "Stripe-Signature": "t=1234567890,v1=invalid_signature"
            },
            json={
                "id": "evt_test_123",
                "type": "checkout.session.completed"
            }
        )

        # 应返回 400 (签名验证失败)
        self.assert_bad_request(response)

    def test_stripe_webhook_empty_body_rejected(self, anon_client):
        """
        业务规则: 空请求体应被拒绝

        Sad Path: 验证错误
        """
        response = anon_client.post(
            self.ENDPOINT,
            headers={
                "Stripe-Signature": "t=1234567890,v1=test_signature"
            },
            content=b""
        )

        # 应返回 400 (签名验证失败或空 body)
        assert response.status_code in [400, 422], (
            f"空请求体应被拒绝，但返回了 {response.status_code}"
        )

    def test_stripe_webhook_malformed_json_rejected(self, anon_client):
        """
        业务规则: 格式错误的 JSON 应被拒绝

        Sad Path: 验证错误
        """
        response = anon_client.post(
            self.ENDPOINT,
            headers={
                "Stripe-Signature": "t=1234567890,v1=test_signature",
                "Content-Type": "application/json"
            },
            content=b"not valid json"
        )

        # 应返回 400 (签名验证失败) 或 422 (JSON 解析失败)
        assert response.status_code in [400, 422], (
            f"格式错误的 JSON 应被拒绝，但返回了 {response.status_code}"
        )


# ==========================================
# Test: Webhook Security
# ==========================================

@pytest.mark.security
@pytest.mark.p0
class TestWebhookSecurity(BaseAPITest):
    """
    Webhook 安全测试

    验证:
    1. 重放攻击防护 (通过签名时间戳验证)
    2. 签名必须有效
    3. 请求体完整性
    """

    def test_clerk_replay_attack_prevention(self, anon_client):
        """
        安全规则: 过期的时间戳应被拒绝 (防止重放攻击)

        注意: Svix 签名包含时间戳，过期请求应被拒绝
        """
        # 使用很旧的时间戳
        response = anon_client.post(
            Endpoints.WEBHOOKS_CLERK,
            headers={
                "svix-id": "msg_test_123",
                "svix-timestamp": "1000000000",  # 2001 年的时间戳
                "svix-signature": "v1,test_signature"
            },
            json={"type": "user.created", "data": {}}
        )

        # 应被拒绝 (时间戳过期或签名无效)
        assert response.status_code in [400, 500], (
            f"过期时间戳应被拒绝，但返回了 {response.status_code}"
        )

    def test_stripe_replay_attack_prevention(self, anon_client):
        """
        安全规则: 过期的时间戳应被拒绝

        Stripe 签名格式: t={timestamp},v1={signature}
        """
        # 使用很旧的时间戳
        response = anon_client.post(
            Endpoints.WEBHOOKS_STRIPE,
            headers={
                "Stripe-Signature": "t=1000000000,v1=test_signature"
            },
            json={"id": "evt_test", "type": "test"}
        )

        # 应被拒绝
        self.assert_bad_request(response)

    def test_clerk_tampered_body_rejected(self, anon_client):
        """
        安全规则: 修改后的请求体应被拒绝 (签名不匹配)
        """
        # 即使有签名 header，如果签名与 body 不匹配也应被拒绝
        response = anon_client.post(
            Endpoints.WEBHOOKS_CLERK,
            headers={
                "svix-id": "msg_test_123",
                "svix-timestamp": "1234567890",
                "svix-signature": "v1,valid_looking_but_wrong_signature"
            },
            json={"type": "user.created", "data": {"tampered": True}}
        )

        assert response.status_code in [400, 500], (
            f"被篡改的请求体应被拒绝，但返回了 {response.status_code}"
        )
